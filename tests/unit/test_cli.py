import pytest

from speedrun import paths
from speedrun.cli import main

SUBCOMMANDS = ["extract", "dump-objects", "plan", "compile", "run", "demo"]


def test_help_lists_subcommands(capsys):
    with pytest.raises(SystemExit) as excinfo:
        main(["--help"])
    assert excinfo.value.code == 0
    out = capsys.readouterr().out
    for name in SUBCOMMANDS:
        assert name in out


def test_unknown_subcommand_exits_nonzero():
    with pytest.raises(SystemExit) as excinfo:
        main(["bogus"])
    assert excinfo.value.code != 0


def test_stub_subcommand_returns_2():
    assert main(["plan", "part1"]) == 2


def test_paths_root_is_repo_root():
    assert (paths.ROOT / ".gitmodules").exists()


@pytest.fixture
def fake_game(tmp_path, monkeypatch):
    game = tmp_path / "game"
    monkeypatch.setattr(paths, "GAME_DIR", game)
    monkeypatch.setattr(paths, "CLASSIC_DIR", game / "classic")
    return game


def test_extract_classic_returns_0(fake_game, capsys):
    # Not under GAME_DIR/classic: that is our output dir and detection skips it.
    src = fake_game / "src"
    src.mkdir(parents=True)
    (src / "monkey1.000").write_bytes(b"index")
    (src / "monkey1.001").write_bytes(b"data")

    assert main(["extract"]) == 0

    classic = fake_game / "classic"
    assert (classic / "MONKEY1.000").read_bytes() == b"index"
    assert (classic / "MONKEY1.001").read_bytes() == b"data"
    out = capsys.readouterr().out
    assert f"layout: CLASSIC ({src})" in out
    assert "MONKEY1.000" in out and "MONKEY1.001" in out


def test_extract_se_pak_returns_0(fake_game, capsys):
    fake_game.mkdir()
    (fake_game / "Monkey1.pak").write_bytes(b"pak")

    assert main(["extract"]) == 0

    assert not (fake_game / "classic").exists()
    out = capsys.readouterr().out
    assert "layout: SE_PAK" in out
    assert "reads Monkey1.pak directly" in out


def test_extract_missing_data_returns_1(fake_game, capsys):
    fake_game.mkdir()

    assert main(["extract"]) == 1

    assert "no MI1 data found" in capsys.readouterr().err
