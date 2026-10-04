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


def test_help_lists_command_options(capsys):
    with pytest.raises(SystemExit):
        main(["--help"])
    out = capsys.readouterr().out
    for option in ("--max-ticks", "--seed", "--boot-param", "--replan"):
        assert option in out
    assert "speedrun run" in out and "speedrun demo" in out


@pytest.mark.parametrize("command", ["run", "demo"])
def test_run_demo_options_parse(command):
    from speedrun.cli import build_parser

    args = build_parser().parse_args(
        [command, "part1", "--seed", "7", "--max-ticks", "900", "--replan", "--boot-param", "3"]
    )
    assert (args.segment, args.seed, args.max_ticks, args.replan, args.boot_param) == ("part1", 7, 900, True, 3)
    defaults = build_parser().parse_args([command, "part1"])
    assert (defaults.seed, defaults.max_ticks, defaults.replan, defaults.boot_param) == (1, None, False, None)


def test_compile_defaults_to_part1():
    from speedrun.cli import build_parser

    assert build_parser().parse_args(["compile"]).segment == "part1"


def test_unknown_subcommand_exits_nonzero():
    with pytest.raises(SystemExit) as excinfo:
        main(["bogus"])
    assert excinfo.value.code != 0


def test_plan_missing_segment_returns_1(tmp_path, monkeypatch, capsys):
    # Never touches the real pddl/ tree: pddl/part1 may exist and would launch Fast Downward.
    monkeypatch.setattr(paths, "PDDL_DIR", tmp_path / "pddl")
    monkeypatch.setattr(paths, "PLANS_DIR", tmp_path / "out" / "plans")
    assert main(["plan", "part1"]) == 1
    assert "part1" in capsys.readouterr().err


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
