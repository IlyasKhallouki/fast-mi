"""Fast Downward: run the planner and parse its plan files.

``run_planner`` drives ``third_party/downward/fast-downward.py`` against the
out-of-tree release build (``scripts/build-downward.sh``) and maps the driver's
exit codes to the ``PlannerError`` hierarchy. The facts behind it (command
layout, exit codes, CPU-only limits, orphaned search processes) are in
``docs/research/fast-downward.md``.
"""

import os
import re
import shlex
import signal
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

from speedrun import paths

FD_BUILD = paths.BUILD_DIR / "downward" / "release"  # the driver's --build: NOT .../bin
FD_DRIVER = paths.DOWNWARD_DIR / "fast-downward.py"

# FD writes "; cost = N (general cost)", or "(unit cost)" on unit-cost tasks.
_COST_RE = re.compile(r";\s*cost\s*=\s*(\d+)\b", re.IGNORECASE)
_ACTION_RE = re.compile(r"\(\s*([^()\s][^()]*?)\s*\)")
# The driver treats a plan file without this last line as incomplete (plan_manager.py).
_TRAILER_RE = re.compile(r"^; cost = (\d+) \((unit cost|general cost)\)$")

_LOG_TAIL_LINES = 10


@dataclass
class Plan:
    actions: list[tuple[str, ...]]  # lower-cased action name followed by its args
    cost: int


def parse_plan(text: str) -> Plan:
    """Parse FD plan text: one ``(name arg ...)`` per line, plus an optional cost trailer.

    Blank lines and ``;`` comments are ignored, except ``; cost = N (...)``,
    which sets ``cost``. Without a trailer, ``cost`` is the number of actions.
    Any other line raises ``ValueError``.
    """
    actions: list[tuple[str, ...]] = []
    cost: int | None = None
    for lineno, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        if not line:
            continue
        if line.startswith(";"):
            m = _COST_RE.match(line)
            if m:
                cost = int(m.group(1))
            continue
        m = _ACTION_RE.fullmatch(line)
        if not m:
            raise ValueError(f"plan line {lineno}: not a ground action: {raw!r}")
        actions.append(tuple(m.group(1).lower().split()))
    return Plan(actions=actions, cost=len(actions) if cost is None else cost)


class PlannerError(Exception):
    """Fast Downward did not produce a plan.

    ``returncode`` is the driver's exit code (``None`` when ``run_planner``
    killed it on its own wall-clock budget). ``log_path`` holds the driver's
    combined stdout and stderr.
    """

    def __init__(self, message: str, *, returncode: int | None, log_path: Path):
        super().__init__(message)
        self.returncode = returncode
        self.log_path = log_path


class Unsolvable(PlannerError):
    """The planner proved that no plan exists (exit 10, 11 or 13)."""


class PlannerTimeout(PlannerError):
    """A CPU time limit was hit (exit 21 or 23), or the wall-clock budget ran out."""


class PlannerOOM(PlannerError):
    """A memory limit was hit (exit 20, 22, or the portfolio-only 24)."""


class PlannerCrashed(PlannerError):
    """A planner bug, a signal, an incomplete search, or an unexpected exit code."""


class PlannerInputError(PlannerError):
    """Bad PDDL, options or files, or a feature the search does not support (exit 31, 33, 34, 36, 37)."""


# driver/returncodes.py, as tabulated in docs/research/fast-downward.md section 4.
_EXIT_CODES: dict[int, tuple[type[PlannerError], str]] = {
    10: (Unsolvable, "TRANSLATE_UNSOLVABLE: the translator proved the task unsolvable"),
    11: (Unsolvable, "SEARCH_UNSOLVABLE: the search proved the task unsolvable"),
    12: (PlannerCrashed, "SEARCH_UNSOLVED_INCOMPLETE: an incomplete search gave up (this proves nothing)"),
    13: (Unsolvable, "SEARCH_UNSOLVABLE_WITHIN_BOUND: no plan within the cost bound"),
    20: (PlannerOOM, "TRANSLATE_OUT_OF_MEMORY"),
    21: (PlannerTimeout, "TRANSLATE_OUT_OF_TIME (CPU time limit)"),
    22: (PlannerOOM, "SEARCH_OUT_OF_MEMORY"),
    23: (PlannerTimeout, "SEARCH_OUT_OF_TIME (CPU time limit)"),
    24: (PlannerOOM, "SEARCH_OUT_OF_MEMORY_AND_TIME"),
    30: (PlannerCrashed, "TRANSLATE_CRITICAL_ERROR: translator bug or assertion (e.g. a cost inside `when`)"),
    31: (PlannerInputError, "TRANSLATE_INPUT_ERROR: bad PDDL or translator option"),
    32: (PlannerCrashed, "SEARCH_CRITICAL_ERROR: search bug"),
    33: (PlannerInputError, "SEARCH_INPUT_ERROR: bad search options or SAS file, or plan file not writable"),
    34: (
        PlannerInputError,
        "SEARCH_UNSUPPORTED: the search configuration does not support a feature of the task "
        "(lmcut: conditional effects or axioms)",
    ),
    35: (PlannerCrashed, "DRIVER_CRITICAL_ERROR"),
    36: (PlannerInputError, "DRIVER_INPUT_ERROR: bad driver arguments, missing input files or build"),
    37: (PlannerInputError, "DRIVER_UNSUPPORTED"),
}


def _signal_name(signum: int) -> str:
    try:
        return signal.Signals(signum).name
    except ValueError:
        return f"signal {signum}"


def _classify(rc: int) -> tuple[type[PlannerError], str]:
    if rc in _EXIT_CODES:
        return _EXIT_CODES[rc]
    if rc < 0:  # the driver process itself was killed
        return PlannerCrashed, f"the driver was killed by {_signal_name(-rc)}"
    if rc > 128:  # the driver exits with -N when the search dies of signal N
        signum = 256 - rc
        note = " (this may also be the kernel's kill at the hard CPU limit, i.e. a time-out)"
        return PlannerCrashed, f"the search was killed by {_signal_name(signum)}" + (
            note if signum == signal.SIGKILL else ""
        )
    return PlannerCrashed, f"unexpected driver exit code {rc}"


def _wall_timeout(time_limit_s: int) -> float:
    """Wall-clock budget for one run. FD's own limits are CPU seconds, which a loaded machine stretches."""
    return 2 * time_limit_s + 60


def _kill_group(proc: subprocess.Popen) -> None:
    """Kill the driver and everything it started (the search outlives a killed driver otherwise)."""
    try:
        os.killpg(proc.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    proc.wait()


def _log_tail(log_path: Path) -> str:
    try:
        lines = [line for line in log_path.read_text(errors="replace").splitlines() if line.strip()]
    except OSError:
        return ""
    tail = lines[-_LOG_TAIL_LINES:]
    return "".join(f"\n  | {line}" for line in tail)


def run_planner(
    domain: Path,
    problem: Path,
    plan_file: Path,
    search: str = "astar(lmcut())",
    time_limit_s: int = 600,
    memory_limit: str = "4G",
) -> Plan:
    """Solve ``domain``/``problem`` with Fast Downward and return the plan written to ``plan_file``.

    ``time_limit_s`` is FD's overall CPU-time limit and ``memory_limit`` its
    overall address-space limit (e.g. ``"4G"``). The driver runs in a fresh
    working directory under ``plan_file.parent`` (removed afterwards), in its
    own session, so the whole process group can be killed on a wall-clock
    time-out or an interrupt. Its combined output goes to
    ``plan_file.with_suffix(".log")``. Any failure raises a ``PlannerError``
    subclass carrying the exit code and that log path.
    """
    domain, problem, plan_file = (Path(p).resolve() for p in (domain, problem, plan_file))
    log_path = plan_file.with_suffix(".log")
    plan_file.parent.mkdir(parents=True, exist_ok=True)
    plan_file.unlink(missing_ok=True)  # FD only clears it once the driver gets going

    cmd = [
        sys.executable, str(FD_DRIVER),
        "--build", str(FD_BUILD),
        "--plan-file", str(plan_file),
        "--overall-time-limit", f"{time_limit_s}s",
        "--overall-memory-limit", memory_limit,
        str(domain), str(problem),
        "--search", search,
    ]  # fmt: skip
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")  # no __pycache__ inside the submodule
    wall_timeout = _wall_timeout(time_limit_s)

    with (
        tempfile.TemporaryDirectory(
            prefix=f".{plan_file.stem}-fd-", dir=plan_file.parent, ignore_cleanup_errors=True
        ) as workdir,
        log_path.open("w", encoding="utf-8") as log,
    ):
        log.write(f"# cwd: {workdir}\n# $ {shlex.join(cmd)}\n")
        log.flush()
        proc = subprocess.Popen(
            cmd,
            cwd=workdir,
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=log,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        try:
            rc = proc.wait(timeout=wall_timeout)
        except subprocess.TimeoutExpired:
            _kill_group(proc)
            raise PlannerTimeout(
                f"Fast Downward exceeded its wall-clock budget of {wall_timeout:g}s "
                f"(CPU limit {time_limit_s}s) and was killed; log: {log_path}{_log_tail(log_path)}",
                returncode=None,
                log_path=log_path,
            ) from None
        except BaseException:
            _kill_group(proc)
            raise
        if rc < 0:
            _kill_group(proc)  # the driver died; its search child may still be running

    if rc != 0:
        exc, what = _classify(rc)
        raise exc(
            f"Fast Downward exit {rc}: {what}; log: {log_path}{_log_tail(log_path)}",
            returncode=rc,
            log_path=log_path,
        )

    def crashed(problem_: str) -> PlannerCrashed:
        return PlannerCrashed(f"Fast Downward exit 0 but {problem_}; log: {log_path}", returncode=0, log_path=log_path)

    if not plan_file.is_file():
        raise crashed(f"no plan file was written at {plan_file}")
    text = plan_file.read_text(encoding="utf-8")
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines or not _TRAILER_RE.match(lines[-1]):
        raise crashed(f"plan file {plan_file} lacks the final '; cost = N (...)' trailer (incomplete plan)")
    try:
        return parse_plan(text)
    except ValueError as e:
        raise crashed(f"plan file {plan_file} is malformed: {e}") from e


def fd_available() -> bool:
    """True when the driver script and the release build's search binary both exist."""
    return FD_DRIVER.is_file() and (FD_BUILD / "bin" / "downward").is_file()
