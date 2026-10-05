"""Fast boot (``SPEEDRUN_FAST_BOOT``, docs/plan.md C1): the demo fast-forwards the boot
(logo, credits, the lookout opening, the Part One card: 9325 ticks, about 2.6 minutes)
to the segment start, then plays in real time.

Fast boot changes only the real-time waiting between frames, so a run with
``fast=False, fast_boot=True`` must match a fully fast run tick for tick. Playing the
whole segment in real time would take about 6 minutes, so both runs stop at
``max_ticks`` = segment start + ``REAL_TIME_TICKS`` and their traces are compared.
"""

import json
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import NamedTuple

import pytest

from speedrun import paths
from speedrun.engine import EngineConfig, run_engine
from speedrun.segments import load_segment

pytestmark = [pytest.mark.integration, pytest.mark.slow]

SEGMENT = "part1"
SEED = 1
# Seconds of game time the fast-boot run plays in real time after the segment start.
REAL_TIME_TICKS = 600
# Launch to segment_start, in wall time, with the boot fast-forwarded.
BOOT_WALL_LIMIT_S = 15.0
# The real-time stretch may not run faster than this share of its game time.
REAL_TIME_MIN_SHARE = 0.8
FULL_RUN_MAX_TICKS = 300000
FULL_RUN_TIMEOUT_S = 600
# Fast boot + REAL_TIME_TICKS of real time is about 15 s. A broken fast boot would
# play the 2.6-minute boot instead, and is killed well before that.
CAPPED_TIMEOUT_S = 90
POLL_S = 0.01


class TimedRun(NamedTuple):
    records: list[dict]
    segment_start_s: float | None  # launch to the segment_start record, in wall time
    total_s: float  # launch to process exit


def _complete_records(path: Path) -> list[dict]:
    """The trace's records so far; a line still being written is left out."""
    try:
        text = path.read_text(encoding="ascii")
    except FileNotFoundError:
        return []
    return [json.loads(line) for line in text.splitlines(keepends=True) if line.endswith("\n")]


def _run_timed(cfg: EngineConfig) -> TimedRun:
    """Run the engine and time, from launch, when ``segment_start`` reaches the trace.

    The trace is flushed after every record (C5), so polling it from here sees the
    record within ``POLL_S`` of the bridge writing it. A run that ends before a poll
    sees it gets its total wall time, an upper bound.
    """
    trace = cfg.out_dir / "trace.jsonl"
    seen = None
    with ThreadPoolExecutor(max_workers=1) as pool:
        launched = time.monotonic()
        future = pool.submit(run_engine, cfg)
        while not future.done():
            if seen is None and any(r["type"] == "segment_start" for r in _complete_records(trace)):
                seen = time.monotonic() - launched
            time.sleep(POLL_S)
        total = time.monotonic() - launched
        result = future.result()
    log = result.log_path.read_text(errors="replace")
    assert not result.timed_out, f"killed after {cfg.timeout_s:g}s of wall time ({cfg.out_dir}):\n{log[-4000:]}"
    records = _complete_records(trace)
    if seen is None and any(r["type"] == "segment_start" for r in records):
        seen = total
    return TimedRun(records=records, segment_start_s=seen, total_s=total)


def _one(records: list[dict], kind: str) -> dict:
    found = [r for r in records if r["type"] == kind]
    assert len(found) == 1, f"expected one {kind!r} record, got {found}"
    return found[0]


@pytest.fixture(scope="module")
def time_plan() -> Path:
    plan = paths.PLANS_DIR / f"{SEGMENT}.time.jsonl"
    if not plan.is_file():
        pytest.skip(f"TIME PLAN MISSING: {plan} not found; run `uv run speedrun optimize {SEGMENT}`")
    return plan


def _config(out_dir: Path, plan: Path, **kw) -> EngineConfig:
    """``speedrun run``'s configuration (``cli.run_segment``), headless, plus ``kw``."""
    seg = load_segment(SEGMENT)
    return EngineConfig(
        out_dir=out_dir,
        plan=plan,
        start=seg.start,
        goal=seg.goal,
        seed=SEED,
        inventory=None if seg.inventory is None else {k: v for k, v in seg.inventory.items() if k != "cite"},
        interrupts=seg.interrupts,
        headless=True,
        **kw,
    )


def test_fast_boot_matches_a_fast_run(engine_ready, time_plan, tmp_path, home_scummvm_guard):
    # (a) Fully fast, to the goal: where the segment starts.
    full = _run_timed(_config(tmp_path / "fast", time_plan, fast=True,
                              max_ticks=FULL_RUN_MAX_TICKS, timeout_s=FULL_RUN_TIMEOUT_S))  # fmt: skip
    tick0 = _one(full.records, "segment_start")["tick0"]
    max_ticks = tick0 + REAL_TIME_TICKS

    # (c) The reference: fast throughout, stopped at max_ticks.
    ref = _run_timed(_config(tmp_path / "ref", time_plan, fast=True,
                             max_ticks=max_ticks, timeout_s=CAPPED_TIMEOUT_S))  # fmt: skip
    # (b) The demo's pacing, headless: fast boot, then real time.
    demo = _run_timed(_config(tmp_path / "fast-boot", time_plan, fast=False, fast_boot=True,
                              max_ticks=max_ticks, timeout_s=CAPPED_TIMEOUT_S))  # fmt: skip

    assert demo.segment_start_s is not None, demo.records[-5:]
    end = _one(demo.records, "end")
    real_time_s = demo.total_s - demo.segment_start_s
    print(
        f"segment start at tick {tick0}; launch to segment_start: fast boot {demo.segment_start_s:.2f}s, "
        f"fully fast {full.segment_start_s:.2f}s; real-time stretch {end['tick'] - tick0} ticks "
        f"in {real_time_s:.2f}s wall (fast-boot run {demo.total_s:.2f}s in all)"
    )

    # The boot records differ only in the pacing switches (C5).
    demo_boot, ref_boot = dict(demo.records[0]), dict(ref.records[0])
    assert demo_boot["type"] == ref_boot["type"] == "boot"
    assert (demo_boot.pop("fast"), demo_boot.pop("fast_boot")) == (False, True)
    assert (ref_boot.pop("fast"), ref_boot.pop("fast_boot")) == (True, False)
    assert demo_boot == ref_boot

    # Same ticks, frames and fingerprint at max_ticks; in fact the same trace.
    assert end["reason"] == "max_ticks", demo.records[-5:]
    assert end["tick"] >= max_ticks
    assert end == _one(ref.records, "end")
    assert demo.records[1:] == ref.records[1:]
    assert _one(demo.records, "segment_start")["tick0"] == tick0

    # The boot is fast-forwarded ...
    assert demo.segment_start_s < BOOT_WALL_LIMIT_S, f"boot took {demo.segment_start_s:.1f}s of wall time"
    # ... and the segment is not: from segment_start on, SPEEDRUN_FAST (off) decides.
    game_s = (end["tick"] - tick0) / 60
    assert real_time_s >= REAL_TIME_MIN_SHARE * game_s, (
        f"{end['tick'] - tick0} ticks ({game_s:.1f}s of game time) after the segment start "
        f"took only {real_time_s:.2f}s of wall time"
    )
