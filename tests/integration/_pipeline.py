"""The full Part I pipeline for integration tests: dump objects, plan, compile, run.

It does what ``speedrun run part1`` does (``speedrun.cli.run_segment``), but it
calls the library functions directly and writes everything under a work dir
the caller passes in. ``out/objects.json`` and ``out/plans/`` are never
touched. ``run_engine`` still keeps ScummVM's (unused) saves dir under
``out/scummvm/``, like every other integration test; its XDG dirs live in
each run dir.
"""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import NamedTuple

from speedrun.compiler import ObjectIndex, compile_plan, load_steps, write_jsonl
from speedrun.engine import EngineConfig, run_engine
from speedrun.planner import run_planner
from speedrun.segments import Segment, load_segment
from speedrun.trace import Trace, format_table, load_trace, summary

SEGMENT = "part1"

# The object dump stops at the first idle frame on the dock (tick 9325 with
# seed 1 at talkspeed 255; skips start only after the segment start, so they do
# not move it). These are the CLI's own dump budgets (speedrun.cli).
DUMP_MAX_TICKS = 60000
DUMP_TIMEOUT_S = 600
# Seed 1 reaches the goal at about tick 33000 from boot with skips (about 66000
# without), in a few seconds of wall time. Both caps leave a wide margin.
RUN_MAX_TICKS = 300000
RUN_TIMEOUT_S = 600

_LOG_TAIL = 4000


@dataclass(frozen=True)
class CompiledRoute:
    segment: Segment
    plan: Path  # the compiled C4 plan (JSONL)
    steps: list[dict]  # the same plan, as the dicts written to ``plan``


class RouteRun(NamedTuple):
    trace: Trace
    out_dir: Path


def _engine(cfg: EngineConfig) -> Trace:
    """Run the engine to completion and load its trace; a wall-clock time-out fails."""
    result = run_engine(cfg)
    if result.timed_out:
        log = result.log_path.read_text(errors="replace")
        raise AssertionError(
            f"the engine was killed after {cfg.timeout_s:g}s of wall time ({cfg.out_dir}); "
            f"log tail:\n{log[-_LOG_TAIL:]}"
        )
    return load_trace(cfg.out_dir / "trace.jsonl")


def compile_route(work: Path, name: str = SEGMENT) -> CompiledRoute:
    """Dump objects, plan with Fast Downward and compile the plan, all under ``work``."""
    seg = load_segment(name)

    dump_dir = work / "dump"
    dump = _engine(EngineConfig(
        out_dir=dump_dir, dump_objects=True, max_ticks=DUMP_MAX_TICKS, timeout_s=DUMP_TIMEOUT_S,
    ))  # fmt: skip
    objects_path = dump_dir / "objects.json"
    assert dump.end is not None and dump.end.get("reason") == "dump_done", describe(dump, dump_dir)
    assert objects_path.is_file(), f"the bridge reported dump_done but wrote no {objects_path}"

    plans = work / "plans"
    plan = run_planner(seg.domain, seg.problem, plans / f"{name}.sas_plan")
    steps = compile_plan(plan, load_steps(seg.steps), ObjectIndex.from_dump(objects_path))
    jsonl = plans / f"{name}.jsonl"
    write_jsonl(steps, jsonl)
    return CompiledRoute(segment=seg, plan=jsonl, steps=steps)


def run_route(route: CompiledRoute, out_dir: Path, seed: int, *, skips: bool = True, interrupts: bool = True,
              step_states: bool = False) -> RouteRun:  # fmt: skip
    """Replay a compiled route headless and fast, as ``speedrun run`` does.

    It uses the segment's start, goal, inventory and interrupts, and text and cutscene
    skips (on by default, like every v1 run). ``step_states`` writes ``state-step-NNN.json``
    at every ``step_end``.
    """
    seg = route.segment
    cfg = EngineConfig(
        out_dir=out_dir,
        plan=route.plan,
        start=seg.start,
        goal=seg.goal,
        inventory=None if seg.inventory is None else {k: v for k, v in seg.inventory.items() if k != "cite"},
        interrupts=seg.interrupts if interrupts else [],
        skip_text=skips,
        skip_cutscenes=skips,
        step_states=step_states,
        seed=seed,
        headless=True,
        fast=True,
        max_ticks=RUN_MAX_TICKS,
        timeout_s=RUN_TIMEOUT_S,
    )
    return RouteRun(trace=_engine(cfg), out_dir=out_dir)


def load_state(path: Path) -> dict:
    """A C7 state dump (``state-start.json`` / ``state-end.json``)."""
    return json.loads(path.read_text(encoding="ascii"))


def holds(cond: dict, state: dict) -> bool:
    """Evaluate one C3 condition against a C7 state dump.

    The dump has no actor positions or rooms, so the ``actor_*`` kinds raise
    rather than pass.
    """
    if "not" in cond:
        return not holds(cond["not"], state)
    if "var" in cond:
        return state["vars"][cond["var"]] == cond["eq"]
    if "bit" in cond:
        return int(cond["bit"] in state["bits_set"]) == cond["eq"]
    if "room" in cond:
        return state["room"] == cond["room"]
    if "owner" in cond:
        return state["owners"].get(str(cond["owner"])) == cond["eq"]
    if "state" in cond:
        return state["states"].get(str(cond["state"])) == cond["eq"]
    if "has" in cond:
        return cond["has"] in state["inventory"]
    raise ValueError(f"cannot evaluate condition {cond!r} against a state dump")


def describe(trace: Trace, out_dir: Path) -> str:
    """Failure context: the summary, the end record and the last steps of the table."""
    table = format_table(trace).splitlines()
    return "\n".join([
        summary(trace),
        f"end: {trace.end}",
        *(f"stall: {s}" for s in trace.stalls[-5:]),
        "last steps:",
        *table[-8:],
        f"run dir: {out_dir}",
        f"engine log: {out_dir / 'stdout.log'}",
    ])  # fmt: skip
