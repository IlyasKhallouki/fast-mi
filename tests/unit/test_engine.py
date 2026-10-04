"""Unit tests for the ScummVM launcher. None of these launch ScummVM; the
run_engine tests use tiny shell scripts as a fake binary."""

import json
import signal
import subprocess
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
    assert engine.saves_dir() == isolated_out / "scummvm" / "saves"


def test_ini_path_is_per_run(tmp_path, isolated_out):
    # The engine rewrites its config file, so every run gets its own copy.
    cfg = _cfg(tmp_path)
    assert engine.ini_path(cfg) == cfg.out_dir / "scummvm.ini"
    other = engine.EngineConfig(out_dir=tmp_path / "other")
    assert engine.ini_path(other) != engine.ini_path(cfg)


def test_argv_has_isolated_config_and_target(tmp_path, isolated_out):
    cfg = _cfg(tmp_path)
    argv = engine.build_argv(cfg)
    assert argv[0] == str(paths.SCUMMVM_BIN)
    config = Path(_value(argv, "--config="))
    assert config == engine.ini_path(cfg)
    assert config.is_relative_to(cfg.out_dir)
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


def test_argv_disables_sdl_audio_and_passes_seed(tmp_path):
    # --disable-sdl-audio gives the null mixer, which the bridge pumps on ticks;
    # the RNG seed goes through ScummVM's own --random-seed (session domain).
    argv = engine.build_argv(_cfg(tmp_path, seed=7, extra_args=["--debuglevel=1"]))
    assert argv.count("--disable-sdl-audio") == 1
    assert _value(argv, "--random-seed=") == "7"
    extra = argv.index("--debuglevel=1")
    assert argv.index("--disable-sdl-audio") < extra
    assert argv.index("--random-seed=7") < extra


def test_argv_default_seed(tmp_path):
    argv = engine.build_argv(_cfg(tmp_path))
    assert _value(argv, "--random-seed=") == "1"
    assert "--disable-sdl-audio" in argv


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
    assert "SPEEDRUN_SEED" not in env
    assert env["SPEEDRUN_MAX_TICKS"] == "1000"
    assert env["SPEEDRUN_STEP_TIMEOUT"] == "50"
    assert env["SDL_VIDEODRIVER"] == "dummy"
    assert env["SDL_AUDIODRIVER"] == "dummy"


def test_env_defaults_omit_optional_vars(tmp_path):
    cfg = _cfg(tmp_path, fast=False)
    env = engine.build_env(cfg, base_env={})
    assert env["SPEEDRUN_OUT"] == str(cfg.out_dir)
    assert "SPEEDRUN_SEED" not in env
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
    assert path == engine.ini_path(cfg) == cfg.out_dir / "scummvm.ini"
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
    # No CLI flag exists for vsync; with the dummy video driver it caps runs at 60 fps.
    assert app["vsync"] == "false"

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
    # Determinism pins (research sections 12 and 18).
    assert game["original_gui"] == "false"
    assert game["enhancements"] == "0"
    assert game["talkspeed"] == "60"


def test_ini_creates_saves_and_xdg_dirs(tmp_path):
    # --savepath fails with a usage error if the directory does not exist.
    cfg = _cfg(tmp_path)
    assert not cfg.out_dir.exists()
    engine.write_ini(cfg)
    assert cfg.out_dir.is_dir()
    assert engine.saves_dir().is_dir()
    env = engine.build_env(_cfg(tmp_path), base_env={})
    assert Path(env["XDG_DATA_HOME"]).is_dir()
    assert Path(env["XDG_CACHE_HOME"]).is_dir()


def test_ini_relative_game_path_made_absolute(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    cfg = _cfg(tmp_path, game_path=Path("game/classic"))
    engine.write_ini(cfg)
    ini = _parse_ini(engine.ini_path(cfg).read_text())
    assert ini["monkey-mac"]["path"] == str(tmp_path / "game" / "classic")


def test_ini_is_deterministic_and_rewritten(tmp_path):
    cfg = _cfg(tmp_path)
    engine.write_ini(cfg)
    first = engine.ini_path(cfg).read_text()
    engine.ini_path(cfg).write_text("[scummvm]\nlastselectedgame=monkey-mac\n")
    engine.write_ini(cfg)
    assert engine.ini_path(cfg).read_text() == first


def test_run_engine_missing_binary_raises(tmp_path, monkeypatch):
    monkeypatch.setattr(paths, "SCUMMVM_BIN", tmp_path / "nope" / "scummvm")
    with pytest.raises(FileNotFoundError, match="build-scummvm"):
        engine.run_engine(_cfg(tmp_path))


def _fake_binary(tmp_path: Path, body: str) -> Path:
    script = tmp_path / "fake-scummvm"
    script.write_text("#!/bin/sh\n" + body + "\n")
    script.chmod(0o755)
    return script


def test_run_engine_timeout_terminates_gracefully(tmp_path, monkeypatch):
    # SIGTERM first, so ScummVM can quit cleanly and the bridge writes its end record.
    monkeypatch.setattr(paths, "SCUMMVM_BIN", _fake_binary(tmp_path, "exec sleep 30"))
    result = engine.run_engine(_cfg(tmp_path, timeout_s=0.3))
    assert result.timed_out
    assert result.returncode == -signal.SIGTERM


def test_run_engine_timeout_kills_if_term_ignored(tmp_path, monkeypatch):
    # An ignored SIGTERM survives exec, so `sleep` ignores it too.
    monkeypatch.setattr(paths, "SCUMMVM_BIN", _fake_binary(tmp_path, "trap '' TERM\nexec sleep 30"))
    monkeypatch.setattr(engine, "TERM_GRACE_S", 0.3)
    result = engine.run_engine(_cfg(tmp_path, timeout_s=0.3))
    assert result.timed_out
    assert result.returncode == -signal.SIGKILL


def test_run_engine_interrupt_terminates_and_reraises(tmp_path, monkeypatch):
    monkeypatch.setattr(paths, "SCUMMVM_BIN", _fake_binary(tmp_path, "exec sleep 30"))
    procs = []

    class InterruptedPopen(subprocess.Popen):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self._interrupt = True
            procs.append(self)

        def wait(self, timeout=None):
            if self._interrupt:
                self._interrupt = False
                raise KeyboardInterrupt
            return super().wait(timeout)

    monkeypatch.setattr(subprocess, "Popen", InterruptedPopen)
    with pytest.raises(KeyboardInterrupt):
        engine.run_engine(_cfg(tmp_path, timeout_s=30))
    assert len(procs) == 1
    assert procs[0].returncode == -signal.SIGTERM
