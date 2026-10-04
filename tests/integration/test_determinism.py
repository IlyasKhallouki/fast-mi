"""Task 5.3: the full Part I route replays deterministically, and reaches the goal under another seed."""

from itertools import zip_longest

import pytest
from _pipeline import CompiledRoute, describe, run_route

from speedrun.trace import Trace, format_ticks

pytestmark = [pytest.mark.integration, pytest.mark.requires_fd, pytest.mark.slow]

# C5: the end record's fingerprint. Comparing whole end records compares these.
FINGERPRINT = ("room", "audio_frames", "music_timer", "vars_fnv1a")


def _step_ticks(trace: Trace) -> list[tuple[int | None, int | None]]:
    return [(s.start_tick, s.end_tick) for s in trace.steps]


def _first_divergence(a: Trace, b: Trace) -> str:
    """Name the first step whose (start_tick, end_tick) differs between two runs."""
    for i, (sa, sb) in enumerate(zip_longest(a.steps, b.steps)):
        ta = None if sa is None else (sa.start_tick, sa.end_tick)
        tb = None if sb is None else (sb.start_tick, sb.end_tick)
        if ta != tb:
            action = (sa or sb).action
            return f"step {i} ({action}) diverged first: run A (start, end) = {ta}, run B = {tb}"
    return "no step diverged"


def test_full_route_is_deterministic(full_route_compiled: CompiledRoute, tmp_path, home_scummvm_guard):
    a_dir, b_dir = tmp_path / "a", tmp_path / "b"
    a = run_route(full_route_compiled, a_dir, seed=1).trace
    b = run_route(full_route_compiled, b_dir, seed=1).trace
    print(f"seed 1 run A: TOTAL {a.total_ticks}, run B: TOTAL {b.total_ticks}")

    assert a.steps, describe(a, a_dir)
    assert len(a.steps) == len(b.steps), _first_divergence(a, b)
    assert _step_ticks(a) == _step_ticks(b), _first_divergence(a, b)
    assert a.total_ticks == b.total_ticks
    assert a.end is not None and b.end is not None, (a.end, b.end)
    for key in FINGERPRINT:
        assert key in a.end, f"end record has no {key!r}: {a.end}"
    assert a.end == b.end


def test_full_route_with_another_seed(full_route_compiled: CompiledRoute, tmp_path, home_scummvm_guard):
    # The route must not depend on a lucky seed. Seed 2 changes Part I's
    # on-demand random draws (segment.toml randomized_vars note): whether the
    # storekeeper is in the store, and the cook's timer and path. Store and
    # cook step timings, and so the total, may differ from seed 1.
    out_dir = tmp_path / "run"
    trace = run_route(full_route_compiled, out_dir, seed=2).trace
    total = trace.total_ticks
    print(f"seed 2: TOTAL {total} ticks ({'-' if total is None else format_ticks(total)} at 60 Hz), run dir {out_dir}")

    context = describe(trace, out_dir)
    assert trace.reached_goal, context
    assert trace.end is not None and trace.end.get("reason") == "goal", context
    assert trace.errors == [], context
