"""A synthetic stand-in for ``run_engine`` (no ScummVM), shared by the measure and optimize tests.

``SyntheticEngine`` reads the C4 plan the config points at and writes a C5
``trace.jsonl`` whose ticks depend on the seed and the action, the way the
bridge would: ``boot``, ``segment_start``, then ``step_start``/``step_end``
per step, and a ``goal`` record that closes the last step (C5 "Goal
mid-step"). A configured failure writes an ``error``, a ``stall`` and an
``end`` with reason ``error`` instead, and no goal.
"""

import json
import threading
from collections.abc import Callable
from pathlib import Path

from speedrun.engine import EngineResult

TICK0 = 1000

# Room numbers the synthetic walks move between; anything else maps to 900+.
ROOMS = {"dock": 33, "bar": 28, "kitchen": 41, "street": 34, "store": 30, "forest": 58, "map": 85}


def room_of(name: str) -> int:
    return ROOMS.get(name, 900 + sum(map(ord, name)) % 90)


def default_ticks(action: str, seed: int, step: int) -> int:
    """Seed- and action-dependent, never zero: 100 + 10 per character + the seed + 7 per extra step."""
    return 100 + 10 * len(action) + seed + 7 * step


class SyntheticEngine:
    """Callable like ``run_engine(cfg)``; records every config it was given.

    - ``ticks(action, seed, step_in_action)``: a step's own duration.
    - ``wait(action, seed)``: ticks the player waits (``until``) before the
      action's first step starts; they fall between the previous ``step_end``
      and this ``step_start``.
    - ``fail(action, seed)``: True makes the action's first step fail.
    - ``timed_out_seeds`` / ``no_trace_seeds``: runs that time out (after
      writing a partial trace) or write no trace at all.
    - ``barrier``: if set, every call waits on it first (proves parallelism).
    """

    def __init__(
        self,
        ticks: Callable[[str, int, int], int] = default_ticks,
        wait: Callable[[str, int], int] | None = None,
        fail: Callable[[str, int], bool] | None = None,
    ):
        self.ticks = ticks
        self.wait = wait or (lambda action, seed: 0)
        self.fail = fail or (lambda action, seed: False)
        self.timed_out_seeds: set[int] = set()
        self.no_trace_seeds: set[int] = set()
        self.barrier: threading.Barrier | None = None
        self.calls: list = []
        self._lock = threading.Lock()

    def __call__(self, cfg) -> EngineResult:
        with self._lock:
            self.calls.append(cfg)
        if self.barrier is not None:
            self.barrier.wait()
        out = Path(cfg.out_dir)
        out.mkdir(parents=True, exist_ok=True)
        log = out / "stdout.log"
        log.write_text("synthetic engine\n")
        if cfg.seed not in self.no_trace_seeds:
            steps = [json.loads(line) for line in Path(cfg.plan).read_text().splitlines() if line.strip()]
            records = self.trace(steps, cfg.seed, truncate=cfg.seed in self.timed_out_seeds)
            (out / "trace.jsonl").write_text("".join(json.dumps(r) + "\n" for r in records))
        return EngineResult(returncode=0, out_dir=out, log_path=log, timed_out=cfg.seed in self.timed_out_seeds)

    def trace(self, steps: list[dict], seed: int, truncate: bool = False) -> list[dict]:
        tick = TICK0
        room = 33
        records = [
            {"type": "boot", "tick": 0, "frame": 0, "bridge": "speedrun-bridge v1", "seed": seed, "audio_pump": True},
            {"type": "segment_start", "tick": TICK0, "frame": 250, "tick0": TICK0, "room": room},
        ]
        previous_action = None
        step_in_action = 0
        for k, step in enumerate(steps):
            action = step["action"]
            if action != previous_action:
                step_in_action = 0
                tick += self.wait(action, seed)
            else:
                step_in_action += 1
            records.append({"type": "step_start", "step": k, "tick": tick, "frame": k, "action": action, "room": room})
            if step_in_action == 0 and self.fail(action, seed):
                records.append({"type": "stall", "tick": tick + 3600, "frame": k, "reason": "sentence_script",
                                "step": k, "room": room})  # fmt: skip
                records.append({"type": "error", "tick": tick + 36000, "frame": k, "step": k, "code": "step_timeout",
                                "message": f"step {k} timed out, blocked by sentence_script"})  # fmt: skip
                records.append({"type": "end", "tick": tick + 36000, "frame": k, "reason": "error"})
                return records
            if truncate and k == len(steps) // 2:
                return records  # killed mid-run: no end record
            tick += self.ticks(action, seed, step_in_action)
            if k == len(steps) - 1:
                records.append({"type": "goal", "tick": tick, "frame": k, "ticks_from_start": tick - TICK0})
                records.append({"type": "end", "tick": tick, "frame": k, "reason": "goal", "room": room})
                return records
            changes: dict = {"vars": {}, "bits": {}, "inventory": {"added": [], "removed": []}}
            parts = action.split()
            if parts[0] == "walk" and len(parts) == 3 and step_in_action == 0:
                new_room = room_of(parts[2])
                changes["room"] = [room, new_room]
                room = new_room
            records.append({"type": "step_end", "step": k, "tick": tick, "frame": k, "room": room,
                            "ticks": 0, "changes": changes})  # fmt: skip
            previous_action = action
        records.append({"type": "end", "tick": tick, "frame": 0, "reason": "plan_exhausted"})
        return records


def write_plan(path: Path, actions: list[str], steps_per_action: dict[str, int] | None = None) -> Path:
    """A C4 plan with ``steps_per_action[a]`` (default 1) steps per action."""
    lines = []
    for action in actions:
        for _ in range((steps_per_action or {}).get(action, 1)):
            step = {"action": action, "verb": 11, "obj": 501, "obj2": 0, "room": 101, "choose": [], "until": []}
            lines.append(json.dumps(step))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n")
    return path


# --- a toy segment tree for CLI tests ------------------------------------------------

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
T0 = 1_700_000_000 * 10**9  # a fixed mtime base, in ns

TOY_DOMAIN = """\
;; Synthetic toy domain (comments carry parens: walk(ego)).
(define (domain toy)
  (:requirements :strips :typing :negative-preconditions :action-costs)
  (:types room)
  (:constants workshop office - room)
  (:predicates (at ?r - room) (link ?from ?to - room) (has-widget))
  (:functions (total-cost) - number)
  (:action take-widget
    :parameters ()
    :precondition (and (at workshop) (not (has-widget)))
    :effect (and (has-widget) (increase (total-cost) 1)))
  (:action walk
    :parameters (?from ?to - room)
    :precondition (and (at ?from) (link ?from ?to))
    :effect (and (not (at ?from)) (at ?to) (increase (total-cost) 1))))
"""

TOY_PROBLEM = """\
(define (problem toy-1)
  (:domain toy)
  (:init
    (at workshop)
    (link workshop office) ; src: synthetic door
    (= (total-cost) 0))
  (:goal (and (has-widget) (at office)))
  (:metric minimize (total-cost)))
"""


def touch(path: Path, t: int) -> None:
    import os

    os.utime(path, ns=(t, t))


def make_tree(tmp_path: Path, monkeypatch) -> dict:
    """Every ``paths`` dir under tmp, and a toy segment ``toy`` whose model is real PDDL.

    Returns the interesting paths. Inputs get mtime ``T0``.
    """
    import shutil

    from speedrun import paths

    out = tmp_path / "out"
    pddl = tmp_path / "pddl"
    docs = tmp_path / "docs"
    for name, value in (("OUT_DIR", out), ("PLANS_DIR", out / "plans"), ("RUNS_DIR", out / "runs"),
                        ("PDDL_DIR", pddl), ("DOCS_DIR", docs)):  # fmt: skip
        monkeypatch.setattr(paths, name, value)
    seg = pddl / "toy"
    seg.mkdir(parents=True)
    for name in ("segment.toml", "steps.toml"):
        shutil.copyfile(FIXTURES / "segments" / "toy" / name, seg / name)
    (seg / "domain.pddl").write_text(TOY_DOMAIN)
    (seg / "problem.pddl").write_text(TOY_PROBLEM)
    out.mkdir()
    shutil.copyfile(FIXTURES / "objects.json", out / "objects.json")
    for path in (*(seg / n for n in ("segment.toml", "steps.toml", "domain.pddl", "problem.pddl")),
                 out / "objects.json"):  # fmt: skip
        touch(path, T0)
    return {
        "out": out,
        "seg": seg,
        "docs": docs,
        "plans": out / "plans",
        "objects": out / "objects.json",
        "sas_plan": out / "plans" / "toy.sas_plan",
        "jsonl": out / "plans" / "toy.jsonl",
        "time_sas_plan": out / "plans" / "toy.time.sas_plan",
        "time_jsonl": out / "plans" / "toy.time.jsonl",
        "costs": seg / "measured-costs.json",
    }


TOY_PLAN_ACTIONS = ["take-widget", "walk workshop office"]


def write_compiled(tree: dict, mtime: int = T0 + 2 * 10**9) -> None:
    """A fresh action-count plan and its compiled jsonl (the toy's two actions)."""
    tree["plans"].mkdir(parents=True, exist_ok=True)
    tree["sas_plan"].write_text("(take-widget)\n(walk workshop office)\n; cost = 2 (unit cost)\n")
    touch(tree["sas_plan"], mtime - 10**9)
    write_plan(tree["jsonl"], TOY_PLAN_ACTIONS)
    touch(tree["jsonl"], mtime)


def write_time_plan(tree: dict, actions: list[str], mtime: int = T0 + 4 * 10**9) -> None:
    """A measured-costs.json and a time plan newer than it (fresh unless an input is touched later)."""
    from speedrun.engine import timing_settings

    tree["costs"].write_text(json.dumps({"version": 1, "unit": "ticks", "skips": None, "engine": timing_settings(),
                                         "bridges": [], "actions": {"take-widget": {"samples": [30]}}}))  # fmt: skip
    touch(tree["costs"], mtime - 10**9)
    tree["plans"].mkdir(parents=True, exist_ok=True)
    tree["time_sas_plan"].write_text("".join(f"({a})\n" for a in actions) + "; cost = 9 (general cost)\n")
    touch(tree["time_sas_plan"], mtime)
    write_plan(tree["time_jsonl"], actions)
    touch(tree["time_jsonl"], mtime)
