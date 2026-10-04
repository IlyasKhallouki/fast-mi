"""Unit tests for the ScummVM launcher. None of these launch ScummVM."""

import json
from pathlib import Path

import pytest

from speedrun import engine, paths


@pytest.fixture(autouse=True)
def isolated_out(tmp_path, monkeypatch) -> Path:
    out = tmp_path / "out"
    monkeypatch.setattr(paths, "OUT_DIR", out)
    return out


def _cfg(tmp_path: Path, **kw) -> engine.EngineConfig:
    return engine.EngineConfig(out_dir=tmp_path / "run", **kw)


def _value(argv: list[str], prefix: str) -> str:
    matches = [a.removeprefix(prefix) for a in argv if a.startswith(prefix)]
    assert len(matches) == 1, f"expected exactly one {prefix!r} in {argv}"
    return matches[0]


def test_dirs_follow_out_dir_at_call_time(isolated_out):
    assert engine.config_dir() == isolated_out / "scummvm"
    assert engine.ini_path() == isolated_out / "scummvm" / "scummvm.ini"
    assert engine.saves_dir() == isolated_out / "scummvm" / "saves"


def test_argv_has_isolated_config_and_target(tmp_path, isolated_out):
    argv = engine.build_argv(_cfg(tmp_path))
    assert argv[0] == str(paths.SCUMMVM_BIN)
    config = Path(_value(argv, "--config="))
    assert config == engine.ini_path()
    assert config.is_relative_to(isolated_out)
    savepath = Path(_value(argv, "--savepath="))
    assert savepath == engine.saves_dir()
    assert savepath.is_relative_to(isolated_out)
    assert argv[-1] == "monkey-mac" == engine.TARGET
    assert not any(a.startswith("--boot-param") for a in argv)


def test_argv_boot_param(tmp_path):
    argv = engine.build_argv(_cfg(tmp_path, boot_param=42))
    assert _value(argv, "--boot-param=") == "42"
    assert argv[-1] == engine.TARGET
    assert argv.index("--boot-param=42") < len(argv) - 1


def test_argv_boot_param_zero_is_passed(tmp_path):
    argv = engine.build_argv(_cfg(tmp_path, boot_param=0))
    assert "--boot-param=0" in argv


def test_argv_extra_args_before_target(tmp_path):
    argv = engine.build_argv(_cfg(tmp_path, extra_args=["--debuglevel=1", "--foo"]))
    assert argv[-3:] == ["--debuglevel=1", "--foo", engine.TARGET]


def test_env_headless_and_speedrun_vars(tmp_path):
    plan = tmp_path / "plan.jsonl"
    start = [{"kind": "room", "room": 33}]
    goal = [{"kind": "owner", "obj": 123, "owner": 1}]
    cfg = _cfg(
        tmp_path,
        plan=plan,
        start=start,
        goal=goal,
        dump_objects=True,
        seed=7,
        max_ticks=1000,
        step_timeout=50,
    )
    env = engine.build_env(cfg, base_env={"PATH": "/usr/bin"})
    assert env["PATH"] == "/usr/bin"
    assert env["SPEEDRUN_OUT"] == str(cfg.out_dir)
    assert env["SPEEDRUN_PLAN"] == str(plan)
    assert json.loads(env["SPEEDRUN_START"]) == start
    assert json.loads(env["SPEEDRUN_GOAL"]) == goal
    assert env["SPEEDRUN_DUMP_OBJECTS"] == "1"
    assert env["SPEEDRUN_FAST"] == "1"
    assert env["SPEEDRUN_SEED"] == "7"
    assert env["SPEEDRUN_MAX_TICKS"] == "1000"
    assert env["SPEEDRUN_STEP_TIMEOUT"] == "50"
    assert env["SDL_VIDEODRIVER"] == "dummy"
    assert env["SDL_AUDIODRIVER"] == "dummy"


def test_env_defaults_omit_optional_vars(tmp_path):
    cfg = _cfg(tmp_path, fast=False)
    env = engine.build_env(cfg, base_env={})
    assert env["SPEEDRUN_OUT"] == str(cfg.out_dir)
    assert env["SPEEDRUN_SEED"] == "1"
    assert json.loads(env["SPEEDRUN_START"]) == []
    assert json.loads(env["SPEEDRUN_GOAL"]) == []
    for absent in (
        "SPEEDRUN_PLAN",
        "SPEEDRUN_DUMP_OBJECTS",
        "SPEEDRUN_FAST",
        "SPEEDRUN_MAX_TICKS",
        "SPEEDRUN_STEP_TIMEOUT",
    ):
        assert absent not in env


def test_env_strips_inherited_speedrun_vars(tmp_path):
    base = {"SPEEDRUN_PLAN": "x", "SPEEDRUN_BOGUS": "y", "SPEEDRUN_MAX_TICKS": "5", "KEEP": "1"}
    env = engine.build_env(_cfg(tmp_path), base_env=base)
    assert "SPEEDRUN_PLAN" not in env
    assert "SPEEDRUN_BOGUS" not in env
    assert "SPEEDRUN_MAX_TICKS" not in env
    assert env["KEEP"] == "1"
    assert base == {"SPEEDRUN_PLAN": "x", "SPEEDRUN_BOGUS": "y", "SPEEDRUN_MAX_TICKS": "5", "KEEP": "1"}


def test_env_windowed_does_not_force_dummy_drivers(tmp_path):
    env = engine.build_env(_cfg(tmp_path, headless=False), base_env={})
    assert "SDL_VIDEODRIVER" not in env
    assert "SDL_AUDIODRIVER" not in env
    env = engine.build_env(
        _cfg(tmp_path, headless=False), base_env={"SDL_VIDEODRIVER": "wayland"}
    )
    assert env["SDL_VIDEODRIVER"] == "wayland"


@pytest.mark.parametrize("headless", [True, False])
def test_env_redirects_xdg_data_and_cache_under_out(tmp_path, isolated_out, headless):
    # ScummVM's POSIX backend unconditionally creates $XDG_DATA_HOME/scummvm/saves
    # and $XDG_CACHE_HOME/scummvm/{icons,dlcs,logs}, even with --config/--savepath.
    home = {"XDG_DATA_HOME": "/home/u/.local/share", "XDG_CACHE_HOME": "/home/u/.cache"}
    env = engine.build_env(_cfg(tmp_path, headless=headless), base_env=home)
    for key in ("XDG_DATA_HOME", "XDG_CACHE_HOME"):
        assert Path(env[key]).is_relative_to(isolated_out)
        assert Path(env[key]).is_relative_to(engine.config_dir())
    assert env["XDG_DATA_HOME"] != env["XDG_CACHE_HOME"]


def _parse_ini(text: str) -> dict[str, dict[str, str]]:
    sections: dict[str, dict[str, str]] = {}
    current = None
    for line in text.splitlines():
        if not line.strip():
            continue
        if line.startswith("["):
            assert line.endswith("]"), line
            current = line[1:-1]
            sections[current] = {}
            continue
        assert current is not None, line
        assert "=" in line and " =" not in line and "= " not in line, line
        key, value = line.split("=", 1)
        sections[current][key] = value
    return sections


def test_ini_contents(tmp_path, isolated_out):
    cfg = _cfg(tmp_path)
    path = engine.write_ini(cfg)
    assert path == engine.ini_path()
    assert path.is_relative_to(isolated_out)
    ini = _parse_ini(path.read_text())
    assert list(ini) == ["scummvm", "monkey-mac"]

    app = ini["scummvm"]
    assert Path(app["savepath"]) == engine.saves_dir()
    assert Path(app["savepath"]).is_relative_to(isolated_out)
    assert app["autosave_period"] == "0"
    assert app["confirm_exit"] == "false"
    assert app["fullscreen"] == "false"
    assert app["gui_return_to_launcher_at_exit"] == "false"
    assert app["extrapath"] == str(paths.ROOT / "third_party/scummvm/dists/engine-data")
    assert app["themepath"] == str(paths.ROOT / "third_party/scummvm/gui/themes")

    game = ini["monkey-mac"]
    assert game["gameid"] == "monkey"
    assert game["engineid"] == "scumm"
    assert Path(game["path"]).is_absolute()
    assert Path(game["path"]) == paths.CLASSIC_DIR.resolve()
    assert game["platform"] == "macintosh"
    assert game["language"] == "en"
    assert game["copy_protection"] == "false"
    assert game["autosave_period"] == "0"
    assert game["subtitles"] == "true"


def test_ini_creates_saves_and_xdg_dirs(tmp_path):
    # --savepath fails with a usage error if the directory does not exist.
    engine.write_ini(_cfg(tmp_path))
    assert engine.saves_dir().is_dir()
    env = engine.build_env(_cfg(tmp_path), base_env={})
    assert Path(env["XDG_DATA_HOME"]).is_dir()
    assert Path(env["XDG_CACHE_HOME"]).is_dir()


def test_ini_relative_game_path_made_absolute(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    engine.write_ini(_cfg(tmp_path, game_path=Path("game/classic")))
    ini = _parse_ini(engine.ini_path().read_text())
    assert ini["monkey-mac"]["path"] == str(tmp_path / "game" / "classic")


def test_ini_is_deterministic_and_rewritten(tmp_path):
    engine.write_ini(_cfg(tmp_path))
    first = engine.ini_path().read_text()
    engine.ini_path().write_text("[scummvm]\nlastselectedgame=monkey-mac\n")
    engine.write_ini(_cfg(tmp_path))
    assert engine.ini_path().read_text() == first


def test_run_engine_missing_binary_raises(tmp_path, monkeypatch):
    monkeypatch.setattr(paths, "SCUMMVM_BIN", tmp_path / "nope" / "scummvm")
    with pytest.raises(FileNotFoundError, match="build-scummvm"):
        engine.run_engine(_cfg(tmp_path))
