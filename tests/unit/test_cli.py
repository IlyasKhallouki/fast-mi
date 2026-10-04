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
