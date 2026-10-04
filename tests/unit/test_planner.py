"""Unit tests for parsing Fast Downward plan files (pure, no FD needed)."""

import pytest

from speedrun.planner import Plan, parse_plan

CANNED = """\
(walk lookout island-map)
(PICK-UP-POT Kitchen)

; a comment that is not the cost trailer
   (open-door)
; cost = 12 (general cost)
"""


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
