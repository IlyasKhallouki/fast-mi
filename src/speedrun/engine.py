"""Isolated launcher for the (patched) ScummVM binary.

ScummVM never touches the user's home:

* ``--config`` points at a per-run ``<out_dir>/scummvm.ini``, so it never
  writes ``~/.config/scummvm/scummvm.ini``. It is per run because the engine
  rewrites its config file (``flushToDisk``), so runs must not share one.
* ``--savepath`` points saves under ``out/scummvm/saves`` (shared: nothing
  ever saves, so nothing writes there).
* ``XDG_DATA_HOME`` / ``XDG_CACHE_HOME`` are redirected to
  ``<out_dir>/xdg/{data,cache}``, one pair per run, because ScummVM's POSIX
  backend unconditionally creates ``$XDG_DATA_HOME/scummvm/saves``
  (``POSIXSaveFileManager``) and ``$XDG_CACHE_HOME/scummvm/{icons,dlcs,logs}``
  (``OSystem_POSIX::getDefault{Icons,DLCs}Path`` / ``getDefaultLogFileName``)
  even when ``--config`` and ``--savepath`` are given. Per-run dirs mean
  parallel runs (``speedrun measure``) never share a file.

Determinism: every launch passes ``--disable-sdl-audio`` (null mixer, which the
bridge pumps on game ticks) and ``--random-seed=<seed>``; the config pins
``vsync=false``, ``original_gui=false``, ``enhancements=0`` and ``talkspeed=255``
(``TALKSPEED``: maximum talk speed, a player setting under rules/glitchless.md).

The patched engine's bridge is configured through ``SPEEDRUN_*`` env vars
(contract C1) and is inert unless ``SPEEDRUN_OUT`` is set. Text and cutscene
skips (``SPEEDRUN_SKIP_TEXT`` / ``SPEEDRUN_SKIP_CUTSCENES``, Phase 8) are on
by default.
"""

import json
import os
import re
import subprocess
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path

from speedrun import paths

TARGET = "monkey-mac"

# After SIGTERM, how long ScummVM gets to quit cleanly (the bridge then writes
# its end record) before SIGKILL.
TERM_GRACE_S = 5.0

# Maximum talk speed. ConfMan's talkspeed range is 0-255 (the options GUI slider,
# gui/options.cpp:575); 241-255 all give getTalkSpeed() 9, so VAR_CHARINC (var 37)
# = 9 - 9 = 0, set at boot through writeVar's room-0 intercept (script.cpp:741).
# Values above 255 are outside the player's range. docs/research/skips-engine.md section 5.
TALKSPEED = 255


def timing_settings() -> dict:
    """The pinned settings that change tick counts. Measurements record them, and
    measurements taken under different values are never pooled or reused."""
    return {"talkspeed": TALKSPEED}


# The bridge sources embed this marker; every trace's boot record carries it as "bridge".
_BRIDGE_MARKER = re.compile(rb"speedrun-bridge v\d+")


class EngineError(Exception):
    """The ScummVM build is unusable (e.g. it carries two bridge markers)."""


def bridge_version(binary: Path | None = None) -> str | None:
    """The bridge identity compiled into the ScummVM binary (``"speedrun-bridge v2"``), or None.

    None when the binary is missing or unpatched. Measurements are only pooled with
    measurements of the same bridge (``speedrun.costing.CostTable``): a rebuilt
    bridge can change timing, and bumps this marker when it does.
    """
    path = paths.SCUMMVM_BIN if binary is None else Path(binary)
    try:
        data = path.read_bytes()
    except OSError:
        return None
    found = sorted({m.decode("ascii") for m in _BRIDGE_MARKER.findall(data)})
    if len(found) > 1:
        raise EngineError(f"{path} carries several bridge markers: {', '.join(found)}")
    return found[0] if found else None


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
    # Inventory slot layout (segment.toml `inventory`); a `cite` key is dropped.
    inventory: dict | None = None
    # Phase 8 skips (C1): inject `.` / Esc after the segment start. On by default.
    skip_text: bool = True
    skip_cutscenes: bool = True
    # Random dialogues answered with a fixed escape (segment.toml `interrupts`); each
    # entry's `cite` is dropped for SPEEDRUN_INTERRUPTS.
    interrupts: list[dict] = field(default_factory=list)
    # Diagnostic: state-step-NNN.json (C7) at every step_end (the skip-safety harness).
    step_states: bool = False
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


def ini_path(cfg: EngineConfig) -> Path:
    """Per-run config file: the engine rewrites it, so runs must not share one."""
    return cfg.out_dir / "scummvm.ini"


def saves_dir() -> Path:
    return config_dir() / "saves"


def _xdg_data_dir(cfg: EngineConfig) -> Path:
    """Per run, so parallel runs never share ScummVM's data dir."""
    return cfg.out_dir / "xdg" / "data"


def _xdg_cache_dir(cfg: EngineConfig) -> Path:
    """Per run, so parallel runs never share ScummVM's cache (and log) dir."""
    return cfg.out_dir / "xdg" / "cache"


def _ini_text(cfg: EngineConfig) -> str:
    # ScummVM's ConfigFile parser wants `key=value` with no spaces around `=`.
    sections = {
        "scummvm": [
            ("savepath", str(saves_dir())),
            ("autosave_period", "0"),
            ("confirm_exit", "false"),
            ("fullscreen", "false"),
            ("gui_return_to_launcher_at_exit", "false"),
            # No CLI flag exists; with SDL's dummy video driver vsync caps runs at 60 fps.
            ("vsync", "false"),
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
            # MI1's boot forces subtitles on anyway (global/script-001.txt [0005] writes
            # VAR_NOSUBTITLES = 0, which writeVar stores in ConfMan); pinned for clarity.
            ("subtitles", "true"),
            ("original_gui", "false"),
            ("enhancements", "0"),
            # Sets VAR_CHARINC (var 37), the per-character text delay: 0 at TALKSPEED.
            ("talkspeed", str(TALKSPEED)),
        ],
    }
    blocks = []
    for name, items in sections.items():
        lines = [f"[{name}]", *(f"{k}={v}" for k, v in items)]
        blocks.append("\n".join(lines) + "\n")
    return "\n".join(blocks)


def write_ini(cfg: EngineConfig) -> Path:
    """(Re)write the run's ScummVM config and create the dirs it relies on.

    The saves dir must exist (``--savepath`` rejects a missing path), and the
    XDG prefixes must exist for ScummVM to put its cache/data under them.
    """
    path = ini_path(cfg)
    for d in (cfg.out_dir, config_dir(), saves_dir(), _xdg_data_dir(cfg), _xdg_cache_dir(cfg)):
        d.mkdir(parents=True, exist_ok=True)
    path.write_text(_ini_text(cfg))
    return path


def build_argv(cfg: EngineConfig) -> list[str]:
    return [
        str(paths.SCUMMVM_BIN),
        f"--config={ini_path(cfg)}",
        f"--savepath={saves_dir()}",
        *([f"--boot-param={cfg.boot_param}"] if cfg.boot_param is not None else []),
        "--disable-sdl-audio",
        f"--random-seed={cfg.seed}",
        *cfg.extra_args,
        TARGET,
    ]


def build_env(cfg: EngineConfig, base_env: Mapping[str, str] | None = None) -> dict[str, str]:
    source = os.environ if base_env is None else base_env
    env = {k: v for k, v in source.items() if not k.startswith("SPEEDRUN_")}

    env["SPEEDRUN_OUT"] = str(cfg.out_dir)
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
    if cfg.inventory is not None:
        layout = {k: v for k, v in cfg.inventory.items() if k != "cite"}
        env["SPEEDRUN_INVENTORY"] = json.dumps(layout)
    if cfg.skip_text:
        env["SPEEDRUN_SKIP_TEXT"] = "1"
    if cfg.skip_cutscenes:
        env["SPEEDRUN_SKIP_CUTSCENES"] = "1"
    if cfg.interrupts:
        keep = ("name", "when", "choose")
        env["SPEEDRUN_INTERRUPTS"] = json.dumps([{k: i[k] for k in keep} for i in cfg.interrupts])
    if cfg.step_states:
        env["SPEEDRUN_STEP_STATES"] = "1"

    # Keep ScummVM's unconditional data/cache dirs out of $HOME (see module doc).
    env["XDG_DATA_HOME"] = str(_xdg_data_dir(cfg))
    env["XDG_CACHE_HOME"] = str(_xdg_cache_dir(cfg))

    if cfg.headless:
        env["SDL_VIDEODRIVER"] = "dummy"
        env["SDL_AUDIODRIVER"] = "dummy"
    return env


def _stop(proc: subprocess.Popen) -> None:
    """SIGTERM, then SIGKILL if the process has not exited within TERM_GRACE_S."""
    if proc.poll() is not None:
        return
    proc.terminate()
    try:
        proc.wait(timeout=TERM_GRACE_S)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()


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
            _stop(proc)
        except BaseException:
            # e.g. KeyboardInterrupt: never leave an orphaned ScummVM behind.
            _stop(proc)
            raise

    return EngineResult(
        returncode=proc.returncode,
        out_dir=cfg.out_dir,
        log_path=log_path,
        timed_out=timed_out,
    )
