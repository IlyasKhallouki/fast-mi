"""Unit tests for the Fast Downward wrapper.

``parse_plan`` and the exit-code mapping are pure (the mapping runs a fake
driver script in place of ``fast-downward.py``). The ``requires_fd`` tests run
the real planner on the toy PDDL in ``tests/fixtures/pddl``.
"""

import json
import subprocess
import time
from pathlib import Path

import pytest

from speedrun import planner
from speedrun.planner import (
    Plan,
    PlannerCrashed,
    PlannerError,
    PlannerInputError,
    PlannerOOM,
    PlannerTimeout,
    Unsolvable,
    fd_available,
    parse_plan,
    run_planner,
)

PDDL = Path(__file__).resolve().parents[1] / "fixtures" / "pddl"
TOY_DOMAIN = PDDL / "toy-domain.pddl"
TOY_PROBLEM = PDDL / "toy-problem.pddl"

CANNED = """\
(walk lookout island-map)
(PICK-UP-POT Kitchen)

; a comment that is not the cost trailer
   (open-door)
; cost = 12 (general cost)
"""


# --- parse_plan --------------------------------------------------------------


def test_parse_plan():
    plan = parse_plan(CANNED)
    assert plan == Plan(
        actions=[
            ("walk", "lookout", "island-map"),
            ("pick-up-pot", "kitchen"),
            ("open-door",),
        ],
        cost=12,
    )


def test_parse_plan_unit_cost_trailer():
    assert parse_plan("(a)\n(b)\n; cost = 7 (unit cost)\n").cost == 7


def test_parse_plan_without_trailer_cost_is_action_count():
    plan = parse_plan("(a x)\n(b y)\n(c)\n")
    assert plan.cost == 3
    assert len(plan.actions) == 3


def test_parse_plan_empty():
    assert parse_plan("") == Plan(actions=[], cost=0)


@pytest.mark.parametrize("bad", ["walk a b", "()", "(walk a", "(a) (b)"])
def test_parse_plan_rejects_non_action_lines(bad):
    with pytest.raises(ValueError):
        parse_plan(bad + "\n")


# --- run_planner against a fake driver (no FD needed) --------------------------

# Stands in for fast-downward.py. It records how it was called, optionally
# writes a plan to --plan-file, optionally spawns a sleeping grandchild (to
# check that the whole process group is killed), then exits with FAKE_FD_RC
# (a negative value kills itself with that signal).
FAKE_DRIVER = """\
import json, os, signal, subprocess, sys, time

argv = sys.argv[1:]
record = os.environ.get("FAKE_FD_RECORD")
if record:
    with open(record, "w") as f:
        json.dump({"argv": argv, "cwd": os.getcwd(),
                   "nobytecode": os.environ.get("PYTHONDONTWRITEBYTECODE")}, f)
print("fake driver stdout", flush=True)
print("fake driver stderr", file=sys.stderr)
plan = os.environ.get("FAKE_FD_PLAN")
if plan is not None:
    with open(argv[argv.index("--plan-file") + 1], "w") as f:
        f.write(plan)
pidfile = os.environ.get("FAKE_FD_GRANDCHILD")
if pidfile:
    child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(120)"])
    with open(pidfile + ".tmp", "w") as f:
        f.write(str(child.pid))
    os.replace(pidfile + ".tmp", pidfile)
    time.sleep(120)
rc = int(os.environ.get("FAKE_FD_RC", "0"))
if rc < 0:
    os.kill(os.getpid(), -rc)
sys.exit(rc)
"""


@pytest.fixture
def fake_fd(tmp_path, monkeypatch):
    driver = tmp_path / "fake-fast-downward.py"
    driver.write_text(FAKE_DRIVER)
    monkeypatch.setattr(planner, "FD_DRIVER", driver)
    monkeypatch.setattr(planner, "FD_BUILD", tmp_path / "fake-build")
    for var in ("FAKE_FD_RECORD", "FAKE_FD_PLAN", "FAKE_FD_GRANDCHILD", "FAKE_FD_RC"):
        monkeypatch.delenv(var, raising=False)
    return driver


def _write_task(tmp_path):
    domain, problem = tmp_path / "d.pddl", tmp_path / "p.pddl"
    domain.write_text("(define (domain x))\n")
    problem.write_text("(define (problem y))\n")
    return domain, problem


@pytest.mark.parametrize(
    ("rc", "exc"),
    [
        (10, Unsolvable),  # TRANSLATE_UNSOLVABLE
        (11, Unsolvable),  # SEARCH_UNSOLVABLE
        (13, Unsolvable),  # SEARCH_UNSOLVABLE_WITHIN_BOUND
        (12, PlannerCrashed),  # incomplete search gave up: proves nothing
        (20, PlannerOOM),
        (22, PlannerOOM),
        (24, PlannerOOM),  # portfolios only: out of memory and time
        (21, PlannerTimeout),
        (23, PlannerTimeout),
        (30, PlannerCrashed),
        (32, PlannerCrashed),
        (35, PlannerCrashed),
        (31, PlannerInputError),
        (33, PlannerInputError),
        (34, PlannerInputError),  # feature unsupported by the search configuration
        (36, PlannerInputError),
        (37, PlannerInputError),
        (1, PlannerCrashed),  # portfolio-only "plan found and ..." codes, unexpected here
        (99, PlannerCrashed),
        (241, PlannerCrashed),  # search killed by SIGTERM
        (247, PlannerCrashed),  # search killed by SIGKILL (maybe a CPU-limit kill)
        (-9, PlannerCrashed),  # the driver itself killed by SIGKILL
    ],
)
def test_exit_codes_map_to_typed_errors(fake_fd, tmp_path, monkeypatch, rc, exc):
    monkeypatch.setenv("FAKE_FD_RC", str(rc))
    domain, problem = _write_task(tmp_path)
    plan_file = tmp_path / "out" / "seg.plan"
    with pytest.raises(exc) as excinfo:
        run_planner(domain, problem, plan_file)
    err = excinfo.value
    assert isinstance(err, PlannerError)
    if exc is not Unsolvable:
        assert not isinstance(err, Unsolvable)
    assert err.returncode == rc
    assert err.log_path == plan_file.with_suffix(".log")
    assert str(err.log_path) in str(err)
    log = err.log_path.read_text()
    assert "fake driver stdout" in log and "fake driver stderr" in log


def test_error_hierarchy():
    for exc in (Unsolvable, PlannerTimeout, PlannerOOM, PlannerCrashed, PlannerInputError):
        assert issubclass(exc, PlannerError)
    assert issubclass(PlannerError, Exception)


def test_driver_command_line_and_working_dir(fake_fd, tmp_path, monkeypatch):
    record = tmp_path / "record.json"
    monkeypatch.setenv("FAKE_FD_RECORD", str(record))
    monkeypatch.setenv("FAKE_FD_PLAN", "(walk a b)\n; cost = 1 (unit cost)\n")
    domain, problem = _write_task(tmp_path)
    plan_file = tmp_path / "out" / "seg.plan"

    # Relative inputs must still reach the driver, which runs in a temp dir.
    monkeypatch.chdir(tmp_path)
    plan = run_planner(Path("d.pddl"), Path("p.pddl"), Path("out/seg.plan"), search="astar(blind())",
                       time_limit_s=42, memory_limit="1G")
    assert plan == Plan(actions=[("walk", "a", "b")], cost=1)

    called = json.loads(record.read_text())
    assert called["argv"] == [
        "--build", str(tmp_path / "fake-build"),
        "--plan-file", str(plan_file),
        "--overall-time-limit", "42s",
        "--overall-memory-limit", "1G",
        str(domain), str(problem),
        "--search", "astar(blind())",
    ]  # fmt: skip
    assert called["nobytecode"] == "1"
    cwd = Path(called["cwd"])
    assert cwd not in (tmp_path, plan_file.parent)
    assert not cwd.exists(), "the per-call working directory must be removed"
    assert sorted(p.name for p in plan_file.parent.iterdir()) == ["seg.log", "seg.plan"]


def test_default_limits(fake_fd, tmp_path, monkeypatch):
    record = tmp_path / "record.json"
    monkeypatch.setenv("FAKE_FD_RECORD", str(record))
    monkeypatch.setenv("FAKE_FD_PLAN", "; cost = 0 (unit cost)\n")
    domain, problem = _write_task(tmp_path)
    assert run_planner(domain, problem, tmp_path / "seg.plan") == Plan(actions=[], cost=0)
    argv = json.loads(record.read_text())["argv"]
    assert argv[argv.index("--overall-time-limit") + 1] == "600s"
    assert argv[argv.index("--overall-memory-limit") + 1] == "4G"
    assert argv[-2:] == ["--search", "astar(lmcut())"]


def test_stale_plan_file_is_not_returned(fake_fd, tmp_path, monkeypatch):
    # The driver exits 0 but writes no plan: an old plan file must not be parsed.
    domain, problem = _write_task(tmp_path)
    plan_file = tmp_path / "seg.plan"
    plan_file.write_text("(old plan)\n; cost = 1 (unit cost)\n")
    with pytest.raises(PlannerCrashed) as excinfo:
        run_planner(domain, problem, plan_file)
    assert excinfo.value.returncode == 0
    assert not plan_file.exists()


def test_plan_without_cost_trailer_is_incomplete(fake_fd, tmp_path, monkeypatch):
    monkeypatch.setenv("FAKE_FD_PLAN", "(walk a b)\n(walk b c)\n")
    domain, problem = _write_task(tmp_path)
    with pytest.raises(PlannerCrashed, match="trailer"):
        run_planner(domain, problem, tmp_path / "seg.plan")


def _alive(pid: int) -> bool:
    try:
        stat = Path(f"/proc/{pid}/stat").read_text()
    except FileNotFoundError:
        return False
    return stat.rsplit(")", 1)[1].split()[0] != "Z"  # a zombie is dead, just not reaped yet


def _wait_for(path: Path, deadline_s: float = 30.0) -> None:
    end = time.monotonic() + deadline_s
    while not path.exists():
        assert time.monotonic() < end, f"{path} never appeared"
        time.sleep(0.05)


@pytest.mark.parametrize("how", ["wall-timeout", "interrupt"])
def test_whole_process_group_is_killed(fake_fd, tmp_path, monkeypatch, how):
    pidfile = tmp_path / "grandchild.pid"
    monkeypatch.setenv("FAKE_FD_GRANDCHILD", str(pidfile))
    domain, problem = _write_task(tmp_path)
    plan_file = tmp_path / "seg.plan"

    if how == "wall-timeout":
        # Give the fake driver time to start its grandchild even on a loaded machine.
        monkeypatch.setattr(planner, "_wall_timeout", lambda time_limit_s: 3.0)
        with pytest.raises(PlannerTimeout) as excinfo:
            run_planner(domain, problem, plan_file, time_limit_s=1)
        assert excinfo.value.returncode is None
        assert excinfo.value.log_path == plan_file.with_suffix(".log")
    else:
        real_popen = subprocess.Popen

        class InterruptedPopen(real_popen):
            def wait(self, timeout=None):
                if self.returncode is None and not getattr(self, "_interrupted", False):
                    self._interrupted = True
                    _wait_for(pidfile)
                    raise KeyboardInterrupt
                return super().wait(timeout)

        monkeypatch.setattr(subprocess, "Popen", InterruptedPopen)
        with pytest.raises(KeyboardInterrupt):
            run_planner(domain, problem, plan_file)

    _wait_for(pidfile, deadline_s=1.0)
    grandchild = int(pidfile.read_text())
    end = time.monotonic() + 10.0
    while _alive(grandchild) and time.monotonic() < end:
        time.sleep(0.05)
    assert not _alive(grandchild), "the planner's grandchild survived: process group not killed"


def test_fd_available_reflects_build(tmp_path, monkeypatch):
    driver = tmp_path / "fast-downward.py"
    build = tmp_path / "release"
    monkeypatch.setattr(planner, "FD_DRIVER", driver)
    monkeypatch.setattr(planner, "FD_BUILD", build)
    assert not fd_available()
    driver.write_text("")
    assert not fd_available()
    (build / "bin").mkdir(parents=True)
    (build / "bin" / "downward").write_text("")
    assert fd_available()


def test_fd_paths():
    from speedrun import paths

    assert planner.FD_BUILD == paths.BUILD_DIR / "downward" / "release"
    assert planner.FD_DRIVER == paths.DOWNWARD_DIR / "fast-downward.py"


# --- the real Fast Downward (requires_fd) --------------------------------------

UNREACHABLE_PROBLEM = """\
(define (problem toy-travel-unreachable)
  (:domain toy-travel)
  (:objects a b c d e - location)
  (:init (at a) (visited a) (road a d) (path a b) (path b c) (path c d)
         (= (total-cost) 0))
  (:goal (at e))
  (:metric minimize (total-cost)))
"""

# `powered` is a fluent, so the translator keeps the conditional effect.
WHEN_DOMAIN = """\
(define (domain toy-switch)
  (:requirements :strips :negative-preconditions :conditional-effects :action-costs)
  (:predicates (powered) (on) (lit))
  (:functions (total-cost) - number)
  (:action power-up
    :parameters ()
    :precondition (not (powered))
    :effect (and (powered) (increase (total-cost) 1)))
  (:action press
    :parameters ()
    :precondition (not (on))
    :effect (and (on) (when (powered) (lit)) (increase (total-cost) 1))))
"""

WHEN_PROBLEM = """\
(define (problem toy-switch-1)
  (:domain toy-switch)
  (:init (= (total-cost) 0))
  (:goal (lit))
  (:metric minimize (total-cost)))
"""


@pytest.mark.requires_fd
def test_costs_are_honoured(fd_ready, tmp_path):
    plan_file = tmp_path / "plans" / "toy.plan"
    plan = run_planner(TOY_DOMAIN, TOY_PROBLEM, plan_file, time_limit_s=60, memory_limit="2G")
    # The single (drive a d) is shorter but costs 10; the three walks cost 3.
    assert plan == Plan(actions=[("walk", "a", "b"), ("walk", "b", "c"), ("walk", "c", "d")], cost=3)
    assert len(plan.actions) > 1
    assert plan_file.read_text().rstrip().endswith("; cost = 3 (general cost)")
    log = plan_file.with_suffix(".log")
    assert "Solution found" in log.read_text()
    # output.sas and the per-call working directory are gone.
    assert sorted(p.name for p in plan_file.parent.iterdir()) == ["toy.log", "toy.plan"]


@pytest.mark.requires_fd
def test_unsolvable_raises(fd_ready, tmp_path):
    problem = tmp_path / "unreachable.pddl"
    problem.write_text(UNREACHABLE_PROBLEM)
    plan_file = tmp_path / "unreachable.plan"
    with pytest.raises(Unsolvable) as excinfo:
        run_planner(TOY_DOMAIN, problem, plan_file, time_limit_s=60, memory_limit="2G")
    err = excinfo.value
    assert err.returncode == 11  # SEARCH_UNSOLVABLE
    assert err.log_path == plan_file.with_suffix(".log")
    assert "unsolvable" in err.log_path.read_text().lower()
    assert not plan_file.exists()


@pytest.mark.requires_fd
def test_conditional_effect_rejected_as_unsupported(fd_ready, tmp_path):
    domain, problem = tmp_path / "switch-domain.pddl", tmp_path / "switch-problem.pddl"
    domain.write_text(WHEN_DOMAIN)
    problem.write_text(WHEN_PROBLEM)
    plan_file = tmp_path / "switch.plan"
    with pytest.raises(PlannerInputError) as excinfo:
        run_planner(domain, problem, plan_file, time_limit_s=60, memory_limit="2G")
    err = excinfo.value
    assert err.returncode == 34  # SEARCH_UNSUPPORTED: lmcut has no conditional effects
    assert "does not support conditional effects" in err.log_path.read_text()
