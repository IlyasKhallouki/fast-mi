"""Unit tests for plan and trace statistics (Task 6.2 helper)."""

from pathlib import Path

from speedrun.planner import Plan
from speedrun.stats import PlanStats, TraceStats, plan_stats, trace_stats
from speedrun.trace import load_trace

TRACES = Path(__file__).resolve().parents[1] / "fixtures" / "traces"


def test_plan_stats_counts_walk_transitions():
    plan = Plan(
        actions=[
            ("walk", "dock", "lookout"),
            ("pick-up-pot",),
            ("walk-forest", "a", "b"),
            ("talk", "clerk"),
            ("buy-shovel",),
        ],
        cost=17,
    )
    assert plan_stats(plan) == PlanStats(actions=5, transitions=2, other=3, cost=17)


def test_plan_stats_only_prefix_counts():
    # "sidewalk" contains "walk" but does not start with it.
    plan = Plan(actions=[("sidewalk-sweep",), ("walkway",)], cost=2)
    assert plan_stats(plan) == PlanStats(actions=2, transitions=1, other=1, cost=2)


def test_plan_stats_empty_plan():
    assert plan_stats(Plan(actions=[], cost=0)) == PlanStats(actions=0, transitions=0, other=0, cost=0)


def test_trace_stats_goal():
    t = load_trace(TRACES / "ok.jsonl")
    # 4 steps; only "walk workshop office" changes room (101 -> 102).
    assert trace_stats(t) == TraceStats(steps=4, room_changes=1, ticks=1360)


def test_trace_stats_no_goal():
    t = load_trace(TRACES / "error.jsonl")
    assert trace_stats(t) == TraceStats(steps=2, room_changes=0, ticks=None)
