"""Task 5.3: compile the full Part I plan and replay it headless on the real engine."""

import pytest
from _pipeline import CompiledRoute, RouteRun, describe, holds, load_state, run_route

from speedrun.trace import format_ticks

pytestmark = [pytest.mark.integration, pytest.mark.requires_fd, pytest.mark.slow]

# docs/part1/goal-flags.md: global script 71 sets Bit[83 + trial]; 85 is the
# idol trial and 86 the treasure trial.
GOAL_BITS = {85, 86}


@pytest.fixture(scope="module")
def full_route_run(full_route_compiled, tmp_path_factory, home_scummvm_guard_factory) -> RouteRun:
    """One headless, fast replay of the full plan with seed 1: ``(trace, out_dir)``."""
    with home_scummvm_guard_factory():
        return run_route(full_route_compiled, tmp_path_factory.mktemp("full-route-seed1") / "run", seed=1)


def test_full_route_reaches_goal(full_route_run: RouteRun, full_route_compiled: CompiledRoute):
    trace, out_dir = full_route_run
    context = describe(trace, out_dir)
    assert trace.goal is not None, context
    assert trace.end is not None and trace.end.get("reason") == "goal", context
    assert trace.errors == [], context

    state_path = out_dir / "state-end.json"
    assert state_path.is_file(), f"no {state_path}\n{context}"
    state = load_state(state_path)
    assert state["tick"] == trace.goal["tick"], (state["tick"], trace.goal)
    assert GOAL_BITS <= set(state["bits_set"]), state["bits_set"]
    goal = full_route_compiled.segment.goal
    assert goal, "segment.toml has no goal conditions"
    failing = [c for c in goal if not holds(c, state)]
    assert failing == [], f"goal conditions false in {state_path}: {failing}"

    total = trace.total_ticks
    assert isinstance(total, int) and not isinstance(total, bool) and total > 0, total
    assert trace.goal["ticks_from_start"] == total, trace.goal
    print(f"seed 1: TOTAL {total} ticks ({format_ticks(total)} at 60 Hz), run dir {out_dir}")


def test_full_route_every_step_started(full_route_run: RouteRun, full_route_compiled: CompiledRoute):
    trace, out_dir = full_route_run
    planned = [s["action"] for s in full_route_compiled.steps]
    n = len(planned)
    context = describe(trace, out_dir)

    started = {s.index: s for s in trace.steps if s.start_tick is not None}
    assert [i for i in range(n) if i not in started] == [], f"steps with no step_start\n{context}"
    assert [s.index for s in trace.steps] == list(range(n)), "the trace has steps beyond the plan"
    assert [started[i].action for i in range(n)] == planned

    # The goal fires during the last step, so only that one may lack a step_end (C5 "Goal mid-step").
    unfinished = [s.index for s in trace.steps if not s.finished]
    assert unfinished in ([], [n - 1]), f"steps with no step_end: {unfinished}\n{context}"
