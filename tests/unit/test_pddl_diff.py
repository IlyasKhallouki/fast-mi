"""Comparing the hand-written model with the extracted one (``speedrun.pddl_diff``) on a toy pair."""

import json
import tomllib

import pytest
from _extract_toy import FRAGMENTS, HAND_DOMAIN, HAND_PROBLEM, HAND_STEPS, OBJECTS, action

from speedrun.compiler import ObjectIndex
from speedrun.pddl_diff import Signature, diff, index_from_script_dump

RUB_COIN = action(
    "rub-coin-in-hall",
    src=("; src: data/scripts/room-090-yard/obj-0904-coin.txt [0016] — Use 904",),
    inputs=("; sentence: 7 904",),
    room="; room: 91",
    pre="(and (at-r91) (has-o904))",
    eff="(and (bit-120) (increase (total-cost) 1))",
)
EXTRACTED = FRAGMENTS | {"misc.pddl": RUB_COIN}


@pytest.fixture
def report():
    steps = tomllib.loads(HAND_STEPS)
    return diff(HAND_DOMAIN, HAND_PROBLEM, steps, ObjectIndex.from_dict(OBJECTS), EXTRACTED)


def _match(report, name: str):
    return next(m for m in report.matched if name in [a.name for a in m.hand])


def test_actions_match_by_player_input_signature(report):
    pairs = sorted(
        (h.name, e.name) for m in report.matched for h in m.hand for e in m.extracted
    )
    assert pairs == [
        ("open-door", "open-door"),
        ("pick-up-coin", "pick-up-coin"),
        ("rub-coin", "rub-coin-in-hall"),  # the hand step has no room: any room matches
        ("take-chest", "take-chest"),  # the hand template's last sentence step (Pick up, not Walk to)
        ("walk hall yard", "walk-hall-to-yard"),  # a ground generic walk
        ("walk-through-door", "walk-yard-to-hall"),
    ]


def test_signatures(report):
    door = _match(report, "walk-through-door")
    assert door.signature == Signature("sentence", 11, 901, 0, 90)
    assert _match(report, "rub-coin").signature == Signature("sentence", 7, 904, 0, None)


def test_hand_only_and_extracted_only(report):
    hand_only = {sig: names for sig, names in report.hand_only}
    assert hand_only == {
        Signature("sentence", 5, 906, 0, 91): ["ring-bell"],
        Signature("sentence", 11, 908, 0, 91): ["walk hall attic"],
        Signature("sentence", 11, 909, 0, 93): ["walk attic hall"],
        Signature("sentence", 11, 910, 0, 93): ["walk attic roof"],
    }
    extracted_only = {sig: names for sig, names in report.extracted_only}
    assert extracted_only == {
        Signature("sentence", 4, 904, 905, 91): ["give-coin-to-statue"],
        Signature("sentence", 11, 907, 0, 91): ["walk-hall-to-cellar"],
        Signature("click", 7, 904, -1, 91): ["wave-coin"],
    }


def test_actions_without_a_signature_are_listed(report):
    assert [name for name, _ in report.hand_unsigned] == ["answer-parrot"]


def test_unresolvable_hand_template_is_listed_not_fatal():
    steps = tomllib.loads(HAND_STEPS)
    steps["actions"]["ring-bell"]["steps"][0]["obj"] = {"room": 91, "name": "gong"}
    report = diff(HAND_DOMAIN, HAND_PROBLEM, steps, ObjectIndex.from_dict(OBJECTS), EXTRACTED)
    unsigned = dict(report.hand_unsigned)
    assert "gong" in unsigned["ring-bell"]


def test_citation_overlap(report):
    door = _match(report, "open-door")
    assert door.cited_by_both == [("room-090-yard/obj-0901-door.txt", "0010")]
    assert door.cited_by_hand_only == [("room-090-yard/obj-0901-door.txt", "0018")]
    assert door.cited_by_extracted_only == []
    chest = _match(report, "take-chest")
    assert chest.cited_by_both == [("room-091-hall/obj-0902-chest.txt", "0015")]
    assert chest.cited_by_extracted_only == [("room-091-hall/obj-0902-chest.txt", "0010")]


def test_ground_walk_cites_its_link(report):
    walk = _match(report, "walk hall yard")
    assert walk.cited_by_both == [("room-091-hall/obj-0903-gate.txt", "000C")]


def test_preconditions_and_effects_side_by_side(report):
    door = _match(report, "walk-through-door")
    (hand,) = door.hand
    (ext,) = door.extracted
    assert hand.pre == ["(at yard)", "(door-open)"]
    assert hand.eff == ["(not (at yard))", "(at hall)"]
    assert ext.pre == ["(at-r90)", "(state-o901-1)"]
    assert ext.eff == ["(not (at-r90))", "(at-r91)"]
    walk = _match(report, "walk hall yard")
    assert walk.hand[0].pre == ["(at hall)", "(link hall yard)"]  # the generic walk, ground
    assert walk.hand[0].eff == ["(not (at hall))", "(at yard)"]


def test_structural_summary(report):
    chest = _match(report, "take-chest")
    assert chest.hand[0].counts == (1, 1, 1, 0)  # (pre +, pre -, add, delete)
    assert chest.extracted[0].counts == (2, 1, 2, 0)


def test_transition_coverage(report):
    links = {(t.source, t.target): (t.hand, t.extracted) for t in report.transitions}
    assert links == {
        (90, 91): (["walk-through-door"], ["walk-yard-to-hall"]),
        (91, 90): (["walk hall yard"], ["walk-hall-to-yard"]),
        (91, 93): (["walk hall attic"], []),
        (93, 91): (["walk attic hall"], []),
        (91, 92): ([], ["walk-hall-to-cellar"]),
    }
    # The roof has no step template of its own, so its room number is unknown.
    assert report.unmapped_links == [("walk attic roof", "attic", "roof")]


def test_markdown(report):
    md = report.to_markdown(title="Extraction diff: toy", notes=["2 extracted actions were rejected."])
    assert md.startswith("# Extraction diff: toy\n")
    assert "2 extracted actions were rejected." in md
    for heading in ("## Summary", "## Matched", "## Hand-only", "## Extracted-only", "## Transitions"):
        assert heading in md
    assert "Walk to 901 in room 90" in md
    assert "`walk-through-door`" in md and "`walk-yard-to-hall`" in md
    assert "(door-open)" in md and "(state-o901-1)" in md
    assert "room-090-yard/obj-0901-door.txt [0018]" in md
    assert "Use 904 (any room)" in md
    assert "click Use + inventory 904 (offset -1) in room 91" in md
    assert "| 91 | 92 |" in md
    assert "answer-parrot" in md
    assert "roof" in md


def test_index_from_script_dump(tmp_path):
    index = {
        "objects": {"901": {"name": "door", "room": 90}, "904": {"name": "coin", "room": 90}},
        "verbs": {"11": {"name": "Walk to"}},
    }
    path = tmp_path / "index.json"
    path.write_text(json.dumps(index))
    objects = index_from_script_dump(path)
    assert objects.resolve_object({"room": 90, "name": "coin"}) == 904
    assert objects.verb_id("Walk to") == 11
