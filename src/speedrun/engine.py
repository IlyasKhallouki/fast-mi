"""Isolated launcher for the (patched) ScummVM binary.

Every launch uses a config file, save dir and XDG data/cache dirs under
``paths.OUT_DIR / "scummvm"`` so ScummVM never touches the user's home:

* ``--config`` keeps it from writing ``~/.config/scummvm/scummvm.ini``.
* ``--savepath`` points saves under ``out/``.
* ``XDG_DATA_HOME`` / ``XDG_CACHE_HOME`` are redirected because ScummVM's POSIX
  backend unconditionally creates ``$XDG_DATA_HOME/scummvm/saves``
  (``POSIXSaveFileManager``) and ``$XDG_CACHE_HOME/scummvm/{icons,dlcs,logs}``
  (``OSystem_POSIX::getDefault{Icons,DLCs}Path`` / ``getDefaultLogFileName``)
  even when ``--config`` and ``--savepath`` are given.

The patched engine's bridge is configured through ``SPEEDRUN_*`` env vars
(contract C1) and is inert unless ``SPEEDRUN_OUT`` is set.
"""

import json
import os
import subprocess
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path

from speedrun import paths

TARGET = "monkey-mac"


@dataclass
class EngineConfig:
    out_dir: Path
    game_path: Path = paths.CLASSIC_DIR
    headless: bool = True
    fast: bool = True
    plan: Path | None = None
    start: list[dict] = field(default_factory=list)
    goal: list[dict] = field(default_factory=list)
    dump_objects: bool = False
    seed: int = 1
    boot_param: int | None = None
    max_ticks: int | None = None
    step_timeout: int | None = None
    timeout_s: float = 600.0
    extra_args: list[str] = field(default_factory=list)


@dataclass
class EngineResult:
    returncode: int
    out_dir: Path
    log_path: Path
    timed_out: bool


# Directory helpers read paths.OUT_DIR at call time so tests can monkeypatch it.


def config_dir() -> Path:
    return paths.OUT_DIR / "scummvm"


def ini_path() -> Path:
    return config_dir() / "scummvm.ini"


def saves_dir() -> Path:
    return config_dir() / "saves"


def _xdg_data_dir() -> Path:
    return config_dir() / "xdg" / "data"


def _xdg_cache_dir() -> Path:
    return config_dir() / "xdg" / "cache"


def _ini_text(cfg: EngineConfig) -> str:
    # ScummVM's ConfigFile parser wants `key=value` with no spaces around `=`.
    sections = {
        "scummvm": [
            ("savepath", str(saves_dir())),
            ("autosave_period", "0"),
            ("confirm_exit", "false"),
            ("fullscreen", "false"),
            ("gui_return_to_launcher_at_exit", "false"),
            ("extrapath", str(paths.ROOT / "third_party" / "scummvm" / "dists" / "engine-data")),
            ("themepath", str(paths.ROOT / "third_party" / "scummvm" / "gui" / "themes")),
        ],
        TARGET: [
            ("gameid", "monkey"),
            ("engineid", "scumm"),
            ("path", str(Path(cfg.game_path).resolve())),
            ("platform", "macintosh"),
            ("language", "en"),
            ("copy_protection", "false"),
            ("autosave_period", "0"),
            ("subtitles", "true"),
        ],
    }
    blocks = []
    for name, items in sections.items():
        lines = [f"[{name}]", *(f"{k}={v}" for k, v in items)]
        blocks.append("\n".join(lines) + "\n")
    return "\n".join(blocks)


def write_ini(cfg: EngineConfig) -> Path:
    """(Re)write the isolated ScummVM config and create the dirs it relies on.

    The saves dir must exist (``--savepath`` rejects a missing path), and the
    XDG prefixes must exist for ScummVM to put its cache/data under them.
    """
    path = ini_path()
    for d in (config_dir(), saves_dir(), _xdg_data_dir(), _xdg_cache_dir()):
        d.mkdir(parents=True, exist_ok=True)
    path.write_text(_ini_text(cfg))
    return path


def build_argv(cfg: EngineConfig) -> list[str]:
    return [
        str(paths.SCUMMVM_BIN),
        f"--config={ini_path()}",
        f"--savepath={saves_dir()}",
        *([f"--boot-param={cfg.boot_param}"] if cfg.boot_param is not None else []),
        *cfg.extra_args,
        TARGET,
    ]


def build_env(cfg: EngineConfig, base_env: Mapping[str, str] | None = None) -> dict[str, str]:
    source = os.environ if base_env is None else base_env
    env = {k: v for k, v in source.items() if not k.startswith("SPEEDRUN_")}

    env["SPEEDRUN_OUT"] = str(cfg.out_dir)
    env["SPEEDRUN_SEED"] = str(cfg.seed)
    env["SPEEDRUN_START"] = json.dumps(cfg.start)
    env["SPEEDRUN_GOAL"] = json.dumps(cfg.goal)
    if cfg.plan is not None:
        env["SPEEDRUN_PLAN"] = str(cfg.plan)
    if cfg.dump_objects:
        env["SPEEDRUN_DUMP_OBJECTS"] = "1"
    if cfg.fast:
        env["SPEEDRUN_FAST"] = "1"
    if cfg.max_ticks is not None:
        env["SPEEDRUN_MAX_TICKS"] = str(cfg.max_ticks)
    if cfg.step_timeout is not None:
        env["SPEEDRUN_STEP_TIMEOUT"] = str(cfg.step_timeout)

    # Keep ScummVM's unconditional data/cache dirs out of $HOME (see module doc).
    env["XDG_DATA_HOME"] = str(_xdg_data_dir())
    env["XDG_CACHE_HOME"] = str(_xdg_cache_dir())

    if cfg.headless:
        env["SDL_VIDEODRIVER"] = "dummy"
        env["SDL_AUDIODRIVER"] = "dummy"
    return env


def run_engine(cfg: EngineConfig) -> EngineResult:
    if not paths.SCUMMVM_BIN.exists():
        raise FileNotFoundError(
            f"ScummVM binary not found at {paths.SCUMMVM_BIN}; "
            "build it with scripts/build-scummvm.sh"
        )
    cfg.out_dir.mkdir(parents=True, exist_ok=True)
    write_ini(cfg)
    argv = build_argv(cfg)
    env = build_env(cfg)
    log_path = cfg.out_dir / "stdout.log"

    timed_out = False
    with log_path.open("wb") as log:
        proc = subprocess.Popen(
            argv,
            stdin=subprocess.DEVNULL,
            stdout=log,
            stderr=subprocess.STDOUT,
            env=env,
        )
        try:
            proc.wait(timeout=cfg.timeout_s)
        except subprocess.TimeoutExpired:
            timed_out = True
            proc.kill()
            proc.wait()
        except BaseException:
            # e.g. KeyboardInterrupt: never leave an orphaned ScummVM behind.
            proc.kill()
            proc.wait()
            raise

    return EngineResult(
        returncode=proc.returncode,
        out_dir=cfg.out_dir,
        log_path=log_path,
        timed_out=timed_out,
    )
