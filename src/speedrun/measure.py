"""Measure a compiled plan's ticks over many seeds, per plan action (Task 8.3).

``measure_plan`` replays one C4 plan headless and fast on every seed, in
parallel (one ``run_engine`` per seed, each in ``<out_dir>/seed-NNN/``), and
turns every trace into per-action durations.

**Per-action durations.** A plan action compiles to one or more steps; the
plan's ``action`` field (echoed in ``step_start``) says which action a step
belongs to, and consecutive steps with the same ``action`` are one plan
action. (Two consecutive equal ground actions would merge, but an optimal
plan never repeats an action back to back: the second application is either
inapplicable or a no-op with a positive cost.) With ``end(X)`` the tick of
action ``X``'s *last* ``step_end``:

- action ``A`` lasts ``end(A) - end(prev(A))``;
- for the first action, ``end(prev) = tick0``;
- the last action ends at the goal tick, whether or not it has a ``step_end``
  (the goal may fire mid-step, C5);
- ends are counted from ``tick0``: an action that ended before the segment
  start lasts 0, and the next one counts from ``tick0``.

So the durations telescope to exactly ``total_ticks`` (goal tick - ``tick0``);
this is asserted for every run. An ``until`` wait (the player waiting for an
NPC before a step may start) falls between the previous ``step_end`` and the
waiting step's ``step_start``, so it counts towards the action that waits
(e.g. the cook wait belongs to ``walk-into-kitchen``). Each instance also
records that wait on its own as ``wait_before``.

**Failures.** A run that does not reach the goal is a failure: it timed out, wrote no
(or a truncated) trace, ended for another reason (``error``, ``max_ticks``,
``plan_exhausted``, ``quit``), ran steps that do not match the plan, reached
the goal before every plan action started, or lacks a ``step_end`` that a later
step implies. A failed run contributes no
durations; its failure names the failing step and action and keeps the
``error`` and ``stall`` records. A missing ScummVM binary aborts the whole
measurement instead.

``summary.json`` (``SUMMARY_VERSION`` 1)::

    {
      "version": 1,
      "segment": "part1",
      "plan": "<the C4 plan measured>",
      "created": "20261004T120000Z",          # UTC
      "seeds": [1, 2, ...],
      "skips": {"text": true, "cutscenes": true},
      "engine": {"talkspeed": 255},          # speedrun.engine.timing_settings()
      "actions": ["open-bar-door", ...],      # one per plan action, in plan order
      "steps_per_action": [1, 1, 2, ...],
      "runs": [                               # one per seed, by seed
        {"seed": 1, "ok": true, "run_dir": "...", "total_ticks": 107660,
         "end_reason": "goal", "timed_out": false, "bridge": "speedrun-bridge v1",
         "instances": [                       # ok runs only; ticks sum to total_ticks
           {"seed": 1, "index": 0, "action": "open-bar-door", "ticks": 354,
            "start_tick": 12865,              # first step_start (absolute, from boot)
            "end_tick": 13219,                # last step_end (the goal for the last action, tick0 at least)
            "wait_before": null,              # previous step_end -> this step_start
            "prev": null,                     # the previous plan action
            "room": 33,                       # ego's room at the first step_start
            "entered_from": null}],           # the room ego entered that room from
         "failure": null},
        {"seed": 2, "ok": false, ..., "instances": [],
         "failure": {"reason": "error", "message": "...", "step": 4, "plan_index": 3,
                     "action": "walk-into-kitchen", "errors": [<error records>],
                     "stalls": [<last stall records>], "end": <end record or null>}}
      ],
      "per_index": [{"index": 0, "action": "...", "n", "mean", "median", "stdev", "min", "max",
                     "failures"}],            # per plan position, over ok runs
      "per_action": {"walk dock lookout": {"n", "mean", "median", "stdev", "min", "max",
                                           "failures", "occurrences"}},  # pooled over positions
      "total": {"n_ok", "n_fail", "n", "mean", "median", "stdev", "min", "max"},  # ok runs
      "per_seed_totals": [{"seed": 1, "ok": true, "total_ticks": 107660}],
      "failures": [{"seed": 2, <failure>}]
    }

``stdev`` is the sample standard deviation, ``null`` with fewer than two
values; ``mean``/``median``/``min``/``max`` are ``null`` with none.
``failures`` counts failed runs whose failing step belongs to that action.

``run_engine`` is called through this module's global, so tests can replace it.
"""

import json
import re
import statistics
from collections.abc import Callable, Iterable
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from speedrun.engine import EngineConfig, run_engine, timing_settings
from speedrun.segments import Segment
from speedrun.trace import Trace, TraceError, format_error, format_ticks, load_trace

SUMMARY_VERSION = 1
DEFAULT_SEEDS = "1-30"
# Wall-clock budget per run. Ticks do not depend on CPU load, but this kill timer does,
# and parallel runs share the CPU: a 15 s run can take minutes on a loaded machine.
MEASURE_TIMEOUT_S = 1800
STALLS_KEPT = 10

_SEED_ITEM = re.compile(r"^(\d+)(?:-(\d+))?$")


class MeasureError(Exception):
    """A plan or trace that cannot be measured (not a per-seed failure)."""


# --- seeds -------------------------------------------------------------------


def parse_seeds(spec: str) -> list[int]:
    """``"1-30"``, ``"1,2,5"`` or a mix (``"1-3,7"``) -> sorted seeds. Raises ``ValueError``."""
    seeds: list[int] = []
    for item in spec.split(","):
        m = _SEED_ITEM.match(item.strip())
        if not m:
            raise ValueError(f"bad seed spec {spec!r}: {item.strip()!r} is not N or N-M")
        lo = int(m.group(1))
        hi = lo if m.group(2) is None else int(m.group(2))
        if hi < lo:
            raise ValueError(f"bad seed spec {spec!r}: empty range {lo}-{hi}")
        seeds.extend(range(lo, hi + 1))
    if len(set(seeds)) != len(seeds):
        raise ValueError(f"bad seed spec {spec!r}: a seed is listed twice")
    return sorted(seeds)


def format_seeds(seeds: Iterable[int]) -> str:
    """The compact spec for a seed list: ``[1, 2, 3, 5]`` -> ``"1-3,5"``."""
    parts: list[str] = []
    run: list[int] = []
    for s in sorted(seeds):
        if run and s == run[-1] + 1:
            run.append(s)
            continue
        if run:
            parts.append(str(run[0]) if len(run) == 1 else f"{run[0]}-{run[-1]}")
        run = [s]
    if run:
        parts.append(str(run[0]) if len(run) == 1 else f"{run[0]}-{run[-1]}")
    return ",".join(parts)


# --- plan steps ----------------------------------------------------------------


@dataclass(frozen=True)
class PlanSteps:
    """A C4 plan, grouped into plan actions."""

    steps: list[dict]
    actions: list[str]  # one per plan action
    step_action: list[int]  # the plan index of each step

    @property
    def steps_per_action(self) -> list[int]:
        counts = [0] * len(self.actions)
        for i in self.step_action:
            counts[i] += 1
        return counts

    def first_step(self, index: int) -> int:
        return self.step_action.index(index)

    def last_step(self, index: int) -> int:
        return len(self.step_action) - 1 - self.step_action[::-1].index(index)


def plan_steps(steps: list[dict]) -> PlanSteps:
    actions: list[str] = []
    step_action: list[int] = []
    for k, step in enumerate(steps):
        action = step.get("action") if isinstance(step, dict) else None
        if not isinstance(action, str) or not action:
            raise MeasureError(f"plan step {k} has no 'action' (C4): {step!r}")
        if not actions or actions[-1] != action:
            actions.append(action)
        step_action.append(len(actions) - 1)
    return PlanSteps(steps=list(steps), actions=actions, step_action=step_action)


def load_plan_steps(path: Path) -> PlanSteps:
    try:
        lines = Path(path).read_text(encoding="utf-8").splitlines()
        steps = [json.loads(line) for line in lines if line.strip()]
    except (OSError, ValueError) as e:
        raise MeasureError(f"cannot read plan {path}: {e}") from e
    if not steps:
        raise MeasureError(f"plan {path} has no steps")
    return plan_steps(steps)


# --- one run -------------------------------------------------------------------


@dataclass
class RunResult:
    seed: int
    run_dir: Path
    ok: bool
    total_ticks: int | None = None
    end_reason: str | None = None
    timed_out: bool = False
    bridge: str | None = None
    instances: list[dict] = field(default_factory=list)
    failure: dict | None = None

    def to_json(self) -> dict:
        return {
            "seed": self.seed,
            "ok": self.ok,
            "run_dir": str(self.run_dir),
            "total_ticks": self.total_ticks,
            "end_reason": self.end_reason,
            "timed_out": self.timed_out,
            "bridge": self.bridge,
            "instances": self.instances,
            "failure": self.failure,
        }


def _failing_step(trace: Trace | None, n_steps: int) -> int | None:
    """The step that failed: an error's step, else the unfinished step, else the next one."""
    if trace is None:
        return None
    for err in trace.errors:
        if isinstance(err.get("step"), int):
            return err["step"]
    started = [s for s in trace.steps if s.start_tick is not None]
    unfinished = [s.index for s in started if not s.finished]
    if unfinished:
        return unfinished[-1]
    following = max((s.index for s in started), default=-1) + 1
    return following if following < n_steps else None


def _failure(
    reason: str, message: str, plan: PlanSteps, trace: Trace | None, step: int | None = None
) -> dict:
    if step is None:
        step = _failing_step(trace, len(plan.steps))
    index = plan.step_action[step] if step is not None and 0 <= step < len(plan.steps) else None
    return {
        "reason": reason,
        "message": message,
        "step": step,
        "plan_index": index,
        "action": None if index is None else plan.actions[index],
        "errors": [] if trace is None else trace.errors,
        "stalls": [] if trace is None else trace.stalls[-STALLS_KEPT:],
        "end": None if trace is None else trace.end,
    }


def _mismatch(trace: Trace, plan: PlanSteps) -> str | None:
    for s in trace.steps:
        if s.start_tick is None:
            continue
        if not 0 <= s.index < len(plan.steps):
            return f"the trace has step {s.index} ({s.action!r}), but the plan has {len(plan.steps)} steps"
        expected = plan.steps[s.index]["action"]
        if s.action != expected:
            return f"trace step {s.index} is {s.action!r}, but the plan's step {s.index} is {expected!r}"
    return None


class _RunFailed(Exception):
    def __init__(self, reason: str, message: str, step: int):
        super().__init__(message)
        self.reason, self.message, self.step = reason, message, step


def _instances(trace: Trace, plan: PlanSteps, seed: int) -> list[dict]:
    """Per-action instances of a goal run; raises ``_RunFailed`` if the trace does not cover the plan."""
    tick0, goal = trace.tick0, trace.goal["tick"]
    by_index = {s.index: s for s in trace.steps}
    n = len(plan.actions)
    for i in range(n):
        first = by_index.get(plan.first_step(i))
        if first is None or first.start_tick is None:
            message = f"the goal fired before plan action {i} ({plan.actions[i]!r}) started"
            raise _RunFailed("goal_before_plan_end", message, plan.first_step(i))
    ends = []
    for i in range(n - 1):
        last = by_index.get(plan.last_step(i))
        if last is None or last.end_tick is None:
            message = (f"plan action {i} ({plan.actions[i]!r}) has no step_end for its last step "
                       f"{plan.last_step(i)}, yet a later action started")  # fmt: skip
            raise _RunFailed("incomplete_trace", message, plan.last_step(i))
        ends.append(last.end_tick)

    # The room ego entered each step's room from: the source of the last room change before it.
    entered_from: dict[int, int | None] = {}
    came_from = None
    for s in trace.steps:
        entered_from[s.index] = came_from
        pair = s.changes.get("room") if s.finished else None
        if isinstance(pair, list) and len(pair) == 2 and pair[0] != pair[1]:
            came_from = pair[0]

    bounds = [tick0] + [max(tick0, t) for t in ends] + [goal]
    instances = []
    for i, action in enumerate(plan.actions):
        k = plan.first_step(i)
        first = by_index[k]
        before = by_index.get(k - 1)
        wait = None if before is None or before.end_tick is None else first.start_tick - before.end_tick
        instances.append({
            "seed": seed,
            "index": i,
            "action": action,
            "ticks": bounds[i + 1] - bounds[i],
            "start_tick": first.start_tick,
            "end_tick": bounds[i + 1],
            "wait_before": wait,
            "prev": plan.actions[i - 1] if i else None,
            "room": first.room_start,
            "entered_from": entered_from.get(k),
        })  # fmt: skip
    total = sum(x["ticks"] for x in instances)
    if total != trace.total_ticks or any(x["ticks"] < 0 for x in instances):
        raise MeasureError(
            f"seed {seed}: action durations {[x['ticks'] for x in instances]} do not sum to "
            f"total_ticks {trace.total_ticks} (tick0 {tick0}, goal {goal}, action ends {ends})"
        )
    return instances


def analyse_run(trace: Trace, plan: PlanSteps, seed: int, run_dir: Path, timed_out: bool = False) -> RunResult:
    """Turn one run's trace into per-action instances, or a failure."""
    result = RunResult(
        seed=seed,
        run_dir=Path(run_dir),
        ok=False,
        end_reason=trace.end.get("reason") if trace.end else None,
        timed_out=timed_out,
        bridge=trace.boot.get("bridge") if trace.boot else None,
    )
    mismatch = _mismatch(trace, plan)
    if mismatch:
        result.failure = _failure("trace_mismatch", mismatch, plan, trace)
        return result
    if not trace.reached_goal:
        if timed_out:
            reason, message = "timed_out", "the engine was killed on its wall-clock timeout before the goal"
        elif trace.end is None:
            reason, message = "no_end", "no end record: the engine was killed or crashed before the goal"
        else:
            reason, message = result.end_reason or "unknown", f"the run ended ({result.end_reason}) before the goal"
        result.failure = _failure(reason, message, plan, trace)
        return result
    if trace.tick0 is None:
        result.failure = _failure("no_segment_start", "goal reached, but no segment_start record", plan, trace)
        return result
    try:
        instances = _instances(trace, plan, seed)
    except _RunFailed as e:
        result.failure = _failure(e.reason, e.message, plan, trace, step=e.step)
        return result
    result.ok = True
    result.total_ticks = trace.total_ticks
    result.instances = instances
    return result


def run_config(seg: Segment, plan: Path, out_dir: Path, seed: int, skips: bool = True) -> EngineConfig:
    """The engine config of one measured run: what ``speedrun run`` uses, plus the skip switches."""
    return EngineConfig(
        out_dir=out_dir,
        plan=Path(plan),
        start=seg.start,
        goal=seg.goal,
        inventory=None if seg.inventory is None else {k: v for k, v in seg.inventory.items() if k != "cite"},
        seed=seed,
        headless=True,
        fast=True,
        skip_text=skips,
        skip_cutscenes=skips,
        timeout_s=MEASURE_TIMEOUT_S,
    )


def _run_seed(seg: Segment, plan_path: Path, plan: PlanSteps, out_dir: Path, seed: int, skips: bool) -> RunResult:
    run_dir = out_dir / f"seed-{seed:03d}"
    result = run_engine(run_config(seg, plan_path, run_dir, seed, skips))  # FileNotFoundError aborts
    try:
        trace = load_trace(run_dir / "trace.jsonl")
    except TraceError as e:
        failure = _failure("no_trace", str(e), plan, None)
        return RunResult(seed=seed, run_dir=run_dir, ok=False, timed_out=result.timed_out, failure=failure)
    return analyse_run(trace, plan, seed, run_dir, timed_out=result.timed_out)


# --- aggregation -----------------------------------------------------------------


def describe(values: list[float]) -> dict:
    """n, mean, median, sample stdev (None below 2 values), min, max."""
    n = len(values)
    if not n:
        return {"n": 0, "mean": None, "median": None, "stdev": None, "min": None, "max": None}
    return {
        "n": n,
        "mean": float(statistics.fmean(values)),
        "median": float(statistics.median(values)),
        "stdev": float(statistics.stdev(values)) if n > 1 else None,
        "min": min(values),
        "max": max(values),
    }


def aggregate(runs: list[RunResult], plan: PlanSteps) -> dict:
    """``per_index``, ``per_action``, ``total``, ``per_seed_totals`` and ``failures`` (see module doc)."""
    ok = [r for r in runs if r.ok]
    failed = [r for r in runs if not r.ok]
    fail_index = [r.failure.get("plan_index") for r in failed]

    per_index = []
    for i, action in enumerate(plan.actions):
        values = [r.instances[i]["ticks"] for r in ok]
        per_index.append({"index": i, "action": action, **describe(values), "failures": fail_index.count(i)})

    per_action: dict[str, dict] = {}
    for action in dict.fromkeys(plan.actions):
        positions = [i for i, a in enumerate(plan.actions) if a == action]
        values = [r.instances[i]["ticks"] for r in ok for i in positions]
        failures = sum(1 for i in fail_index if i in positions)
        per_action[action] = {**describe(values), "failures": failures, "occurrences": len(positions)}

    totals = describe([r.total_ticks for r in ok])
    total = {"n_ok": len(ok), "n_fail": len(failed), **totals}
    return {
        "per_index": per_index,
        "per_action": per_action,
        "total": total,
        "per_seed_totals": [{"seed": r.seed, "ok": r.ok, "total_ticks": r.total_ticks} for r in runs],
        "failures": [{"seed": r.seed, **r.failure} for r in failed],
    }


# --- measure ---------------------------------------------------------------------


def _utc_stamp() -> str:
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")


def measure_plan(
    plan_path: Path,
    seg: Segment,
    seeds: list[int],
    out_dir: Path,
    *,
    jobs: int,
    skips: bool = True,
    progress: Callable[[RunResult], None] | None = None,
) -> dict:
    """Run ``plan_path`` on every seed (``jobs`` at a time), write ``out_dir/summary.json`` and return it."""
    if not seeds:
        raise MeasureError("no seeds to measure")
    plan = load_plan_steps(plan_path)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    results: list[RunResult] = []
    pool = ThreadPoolExecutor(max_workers=max(1, jobs), thread_name_prefix="measure")
    try:
        futures = [pool.submit(_run_seed, seg, Path(plan_path), plan, out_dir, s, skips) for s in seeds]
        for future in as_completed(futures):
            result = future.result()
            results.append(result)
            if progress is not None:
                progress(result)
    except BaseException:
        # A missing binary, a bad trace or Ctrl-C: start no further runs. Running ones finish.
        pool.shutdown(wait=True, cancel_futures=True)
        raise
    pool.shutdown(wait=True)

    results.sort(key=lambda r: r.seed)
    summary = {
        "version": SUMMARY_VERSION,
        "segment": seg.name,
        "plan": str(plan_path),
        "created": _utc_stamp(),
        "seeds": sorted(seeds),
        "skips": {"text": skips, "cutscenes": skips},
        "engine": timing_settings(),
        "actions": plan.actions,
        "steps_per_action": plan.steps_per_action,
        "runs": [r.to_json() for r in results],
        **aggregate(results, plan),
    }
    write_summary(summary, out_dir / "summary.json")
    return summary


def write_summary(summary: dict, path: Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(summary, indent=1) + "\n", encoding="utf-8")
    tmp.replace(path)


def load_summary(path: Path) -> dict:
    summary = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(summary, dict) or summary.get("version") != SUMMARY_VERSION:
        raise MeasureError(f"{path} is not a version {SUMMARY_VERSION} measure summary")
    return summary


# --- reporting -------------------------------------------------------------------


def _num(value, digits: int = 1) -> str:
    if value is None:
        return "-"
    if isinstance(value, float):
        return f"{value:.{digits}f}"
    return str(value)


def format_failure(failure: dict, seed: int | None = None) -> str:
    """A multi-line description of one failed run: where it failed, its errors and last stalls."""
    where = ""
    if failure.get("step") is not None:
        where = f" at step {failure['step']}"
        if failure.get("action") is not None:
            where += f" (plan action {failure['plan_index']} {failure['action']!r})"
    head = f"FAILED seed {seed}" if seed is not None else "FAILED"
    lines = [f"{head}: {failure['reason']}{where}: {failure['message']}"]
    lines += [f"  {format_error(e).strip()}" for e in failure.get("errors") or []]
    for stall in (failure.get("stalls") or [])[-3:]:
        lines.append(f"    stall at tick {stall.get('tick')}: {stall.get('reason')} (step {stall.get('step')})")
    return "\n".join(lines)


def format_total(total: dict) -> str:
    mean = total.get("mean")
    clock = f" ({format_ticks(round(mean))})" if mean is not None else ""
    return (
        f"total: n_ok {total['n_ok']}, n_fail {total['n_fail']}, mean {_num(mean)}{clock}, "
        f"stdev {_num(total.get('stdev'))}, min {_num(total.get('min'))}, max {_num(total.get('max'))}"
    )


def format_summary(summary: dict) -> str:
    """The per-plan-action table, the totals, the per-seed totals and every failure."""
    header = ["#", "action", "n", "mean", "median", "stdev", "min", "max", "fail"]
    rows = [
        [str(r["index"]), r["action"], str(r["n"]), _num(r["mean"]), _num(r["median"]), _num(r["stdev"]),
         _num(r["min"]), _num(r["max"]), str(r["failures"])]
        for r in summary["per_index"]
    ]  # fmt: skip
    widths = [max(len(row[i]) for row in [header, *rows]) for i in range(len(header))]

    def line(cells: list[str]) -> str:
        return "  ".join(c.ljust(w) if i == 1 else c.rjust(w) for i, (c, w) in enumerate(zip(cells, widths)))

    seeds = ", ".join(
        f"{s['seed']}: {s['total_ticks']}" if s["ok"] else f"{s['seed']}: FAILED" for s in summary["per_seed_totals"]
    )
    out = [line(header), *(line(r) for r in rows), "", format_total(summary["total"]), f"per-seed totals: {seeds}"]
    for failure in summary["failures"]:
        run_dir = next((r["run_dir"] for r in summary["runs"] if r["seed"] == failure["seed"]), None)
        out.append(format_failure(failure, failure["seed"]))
        if run_dir:
            out.append(f"    run dir: {run_dir}")
    return "\n".join(out)
