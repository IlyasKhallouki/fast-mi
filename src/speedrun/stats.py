"""Counts for the comparison report (Task 6.2): plan actions and room transitions, trace steps and ticks.

Room transitions in a ``Plan`` are the actions whose name starts with
``walk``: that is the PDDL model's naming convention for moving between rooms.
"""

from dataclasses import dataclass

from speedrun.planner import Plan
from speedrun.trace import Trace

TRANSITION_PREFIX = "walk"


@dataclass(frozen=True)
class PlanStats:
    actions: int  # every ground action in the plan
    transitions: int  # actions whose name starts with "walk"
    other: int  # actions - transitions
    cost: int  # the planner's reported plan cost


@dataclass(frozen=True)
class TraceStats:
    steps: int  # plan steps seen in the trace (finished or not)
    room_changes: int  # steps that ended in a different room than they started in
    ticks: int | None  # segment start to goal, None without a goal


def plan_stats(plan: Plan) -> PlanStats:
    transitions = sum(1 for action in plan.actions if action and action[0].startswith(TRANSITION_PREFIX))
    return PlanStats(
        actions=len(plan.actions),
        transitions=transitions,
        other=len(plan.actions) - transitions,
        cost=plan.cost,
    )


def trace_stats(trace: Trace) -> TraceStats:
    room_changes = sum(
        1
        for s in trace.steps
        if s.room_start is not None and s.room_end is not None and s.room_start != s.room_end
    )
    return TraceStats(steps=len(trace.steps), room_changes=room_changes, ticks=trace.total_ticks)
