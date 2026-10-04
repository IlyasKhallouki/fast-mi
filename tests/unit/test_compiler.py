"""Unit tests for the plan compiler (plan + steps.toml + objects.json -> C4 JSONL).

Everything resolves against the synthetic fixture ``tests/fixtures/objects.json``.
"""

import json
from pathlib import Path

import pytest

from speedrun.compiler import (
    AmbiguousObject,
    CompileError,
    MissingStepTemplate,
    ObjectIndex,
    TemplateError,
    UnknownVerb,
    UnresolvedObject,
    compile_plan,
    load_steps,
    write_jsonl,
)
from speedrun.conditions import ConditionError
from speedrun.planner import Plan

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
TOY_STEPS = FIXTURES / "segments" / "toy" / "steps.toml"

# C4 key order, written out independently of the implementation.
C4_KEYS = ["action", "verb", "obj", "obj2", "room", "choose", "until"]
C4_INT_KEYS = {"verb", "obj", "obj2", "room"}

VERBS = {"walk_to": "Walk to", "pick_up": "Pick up", "talk_to": "Talk to", "give": "Give"}

# Invented verb ids from the fixture.
WALK_TO, PICK_UP, TALK_TO, GIVE = 11, 9, 13, 3


@pytest.fixture(scope="module")
def index() -> ObjectIndex:
    return ObjectIndex.from_dump(FIXTURES / "objects.json")


def _plan(*actions: str) -> Plan:
    return Plan(actions=[tuple(a.split()) for a in actions], cost=len(actions))


def _steps(actions: dict, verbs: dict | None = None) -> dict:
    return {"verbs": VERBS if verbs is None else verbs, "actions": actions}


def _compile_one(index, *templates, action="do-thing") -> list[dict]:
    steps = _steps({action: {"cite": "synthetic", "steps": list(templates)}})
    return compile_plan(_plan(action), steps, index)


def _assert_c4(step: dict) -> None:
    keys = list(step)
    assert set(keys) <= set(C4_KEYS), keys
    assert keys == [k for k in C4_KEYS if k in step], "keys out of C4 order"
    for k in ("action", "choose", "until"):
        assert k in step
    if "verb" in step:
        assert "obj" in step and "obj2" in step
    else:
        assert "obj" not in step and "obj2" not in step
    for k in C4_INT_KEYS & set(step):
        assert type(step[k]) is int, (k, step[k])
    assert all(isinstance(c, str) for c in step["choose"])


# --- object resolution -------------------------------------------------------


@pytest.mark.parametrize("name", ["widget", "WIDGET", "Widget", " widget "])
def test_resolve_unique_name_case_insensitive_padding_stripped(index, name):
    assert index.resolve_object({"room": 101, "name": name}) == 500


def test_resolve_padded_name_in_other_room(index):
    assert index.resolve_object({"room": 102, "name": "door"}) == 510
    assert index.resolve_object({"room": 101, "name": "door"}) == 501


def test_ambiguous_name_without_id_lists_ids(index):
    with pytest.raises(AmbiguousObject) as excinfo:
        index.resolve_object({"room": 101, "name": "crate"})
    assert excinfo.value.ids == [502, 503]
    assert "502" in str(excinfo.value) and "503" in str(excinfo.value)
    assert isinstance(excinfo.value, CompileError)


def test_id_disambiguates(index):
    assert index.resolve_object({"room": 101, "name": "crate", "id": 503}) == 503
    assert index.resolve_object({"room": 101, "name": "widget", "id": 500}) == 500


def test_id_in_wrong_room_is_unresolved(index):
    # 510 is the office door (room 102); room 101 has its own door 501.
    with pytest.raises(UnresolvedObject):
        index.resolve_object({"room": 101, "name": "door", "id": 510})


def test_id_with_wrong_name_is_unresolved(index):
    # 500 exists in room 101 but is the widget, not a door.
    with pytest.raises(UnresolvedObject):
        index.resolve_object({"room": 101, "name": "door", "id": 500})


def test_unknown_id_is_unresolved(index):
    with pytest.raises(UnresolvedObject):
        index.resolve_object({"room": 101, "name": "door", "id": 999})


@pytest.mark.parametrize(
    "ref",
    [
        {"room": 101, "name": "gizmo"},
        {"room": 103, "name": "door"},  # room with no objects
        {"room": 999, "name": "door"},  # room not in the dump
    ],
)
def test_unknown_name_is_unresolved(index, ref):
    with pytest.raises(UnresolvedObject):
        index.resolve_object(ref)


def test_actor_reference_passes_through(index):
    assert index.resolve_object({"actor": 3}) == 3
    assert index.resolve_object({"actor": 1}) == 1


@pytest.mark.parametrize(
    "ref",
    [
        {"actor": 13},  # actors are ids < 13
        {"actor": 0},
        {"actor": True},
        {"actor": "3"},
        {"actor": 3, "room": 101},
        {"room": 101},  # no name
        {"name": "widget"},  # no room
        {"room": 101, "name": ""},
        {"room": "101", "name": "widget"},
        {"room": True, "name": "widget"},
        {"room": 101, "name": "widget", "id": "500"},
        {"room": 101, "name": "widget", "extra": 1},
        "widget",
        500,
    ],
    ids=repr,
)
def test_malformed_reference_is_template_error(index, ref):
    with pytest.raises(TemplateError):
        index.resolve_object(ref)


def test_duplicate_dump_entries_are_not_ambiguous():
    idx = ObjectIndex.from_dict(
        {
            "verbs": [],
            "rooms": [
                {"room": 5, "objects": [{"id": 7, "name": "lamp"}, {"id": 7, "name": "lamp@"}]},
            ],
        }
    )
    assert idx.resolve_object({"room": 5, "name": "lamp"}) == 7


def test_from_dict_tolerates_unnamed_objects():
    idx = ObjectIndex.from_dict(
        {"verbs": [], "rooms": [{"room": 5, "objects": [{"id": 6, "name": None}, {"id": 7, "name": "lamp"}]}]}
    )
    assert idx.resolve_object({"room": 5, "name": "lamp"}) == 7


def test_from_dict_rejects_malformed_dump():
    with pytest.raises(CompileError):
        ObjectIndex.from_dict({"verbs": [], "rooms": [{"objects": []}]})


# --- verbs -------------------------------------------------------------------


@pytest.mark.parametrize(
    ("name", "vid"), [("Walk to", WALK_TO), ("walk TO", WALK_TO), ("pick up", PICK_UP), ("Give", GIVE)]
)
def test_verb_id_case_insensitive(index, name, vid):
    assert index.verb_id(name) == vid


def test_verb_id_unknown(index):
    with pytest.raises(UnknownVerb):
        index.verb_id("Push")


def test_unknown_verb_keyword(index):
    with pytest.raises(UnknownVerb, match="jump"):
        _compile_one(index, {"verb": "jump", "obj": {"room": 101, "name": "widget"}})


def test_verb_name_missing_from_dump(index):
    steps = _steps(
        {"push-lever": {"steps": [{"verb": "push", "obj": {"room": 101, "name": "lever"}}]}},
        verbs={"push": "Push"},
    )
    with pytest.raises(UnknownVerb, match="Push"):
        compile_plan(_plan("push-lever"), steps, index)


# --- compile_plan ------------------------------------------------------------


def test_missing_step_template_names_action(index):
    steps = _steps({"take-widget": {"steps": [{"choose": ["x"]}]}})
    with pytest.raises(MissingStepTemplate, match="walk workshop yard") as excinfo:
        compile_plan(_plan("take-widget", "walk workshop yard"), steps, index)
    assert isinstance(excinfo.value, CompileError)


def test_single_step(index):
    out = _compile_one(
        index, {"verb": "pick_up", "obj": {"room": 101, "name": "widget"}, "room": 101}, action="take-widget"
    )
    assert out == [
        {"action": "take-widget", "verb": PICK_UP, "obj": 500, "obj2": 0, "room": 101, "choose": [], "until": []}
    ]


def test_multi_step_template_expands_in_order(index):
    steps = _steps(
        {
            "buy-ledger": {
                "steps": [
                    {"verb": "pick_up", "obj": {"room": 102, "name": "ledger"}, "room": 102},
                    {"verb": "talk_to", "obj": {"room": 102, "name": "clerk"}, "room": 102, "choose": ["ledger"]},
                ]
            },
            "walk office workshop": {
                "steps": [{"verb": "walk_to", "obj": {"room": 102, "name": "door"}, "room": 102}]
            },
        }
    )
    out = compile_plan(_plan("walk office workshop", "buy-ledger", "walk office workshop"), steps, index)
    assert [(s["action"], s["verb"], s["obj"]) for s in out] == [
        ("walk office workshop", WALK_TO, 510),
        ("buy-ledger", PICK_UP, 512),
        ("buy-ledger", TALK_TO, 511),
        ("walk office workshop", WALK_TO, 510),
    ]
    assert out[2]["choose"] == ["ledger"]


def test_action_string_joins_args(index):
    steps = _steps({"walk workshop office": {"steps": [{"choose": ["x"]}]}})
    plan = Plan(actions=[("walk", "workshop", "office")], cost=1)
    assert compile_plan(plan, steps, index)[0]["action"] == "walk workshop office"


def test_dialogue_only_step_has_no_verb_or_obj(index):
    out = _compile_one(index, {"choose": ["goodbye"]}, action="answer-clerk")
    assert out == [{"action": "answer-clerk", "choose": ["goodbye"], "until": []}]
    assert list(out[0]) == ["action", "choose", "until"]


def test_verbless_step_without_choose_is_rejected(index):
    with pytest.raises(TemplateError):
        _compile_one(index, {"room": 101})
    with pytest.raises(TemplateError):
        _compile_one(index, {"until": [{"room": 101}]})


@pytest.mark.parametrize(
    "tmpl",
    [
        {"obj": {"room": 101, "name": "widget"}, "choose": ["x"]},  # obj without verb
        {"obj2": {"actor": 3}, "choose": ["x"]},
        {"verb": "pick_up"},  # verb without obj
        {"verb": "pick_up", "obj": {"room": 101, "name": "widget"}, "wait": 3},  # unknown key
        {"verb": "pick_up", "obj": {"room": 101, "name": "widget"}, "room": "101"},
        {"verb": "pick_up", "obj": {"room": 101, "name": "widget"}, "room": True},
        {"verb": 9, "obj": {"room": 101, "name": "widget"}},
        {"choose": "ledger"},  # choose must be a list
        {"choose": ["ledger", 3]},
        {"choose": [""]},
        "pick up widget",
    ],
    ids=repr,
)
def test_bad_step_template_is_template_error(index, tmpl):
    with pytest.raises(TemplateError):
        _compile_one(index, tmpl)


@pytest.mark.parametrize(
    "entry",
    [
        {"steps": []},
        {"cite": "x"},
        {"steps": {"choose": ["x"]}},
        {"cite": 3, "steps": [{"choose": ["x"]}]},
        {"cite": "x", "steps": [{"choose": ["x"]}], "note": "y"},
    ],
    ids=repr,
)
def test_bad_action_entry_is_template_error(index, entry):
    with pytest.raises(TemplateError, match="do-thing"):
        compile_plan(_plan("do-thing"), _steps({"do-thing": entry}), index)


def test_choose_and_until_pass_through(index):
    out = _compile_one(
        index,
        {
            "until": [{"var": 250, "eq": 0}, {"not": {"has": 500}}],
            "verb": "talk_to",
            "obj": {"room": 102, "name": "clerk"},
            "room": 102,
            "choose": ["ledger", "yes please"],
        },
    )
    assert out[0]["choose"] == ["ledger", "yes please"]
    assert out[0]["until"] == [{"var": 250, "eq": 0}, {"not": {"has": 500}}]
    _assert_c4(out[0])


def test_invalid_until_is_template_error(index):
    with pytest.raises(TemplateError, match="do-thing") as excinfo:
        _compile_one(index, {"choose": ["x"], "until": [{"var": 250}]})
    assert isinstance(excinfo.value.__cause__, ConditionError)


def test_resolution_error_names_action_and_step(index):
    with pytest.raises(UnresolvedObject, match=r"take-gizmo.*step 1"):
        _compile_one(
            index,
            {"choose": ["x"]},
            {"verb": "pick_up", "obj": {"room": 101, "name": "gizmo"}},
            action="take-gizmo",
        )


def test_obj2_resolves_and_defaults_to_zero(index):
    out = _compile_one(
        index,
        {"verb": "give", "obj": {"room": 101, "name": "widget"}, "obj2": {"actor": 3}},
        {"verb": "give", "obj": {"room": 101, "name": "widget"}, "obj2": {"room": 102, "name": "clerk"}},
        {"verb": "pick_up", "obj": {"room": 101, "name": "lever"}},
    )
    assert [s["obj2"] for s in out] == [3, 511, 0]


def test_output_key_order_and_keys_match_c4(index):
    out = _compile_one(
        index,
        {
            "until": [{"room": 101}],
            "choose": ["a"],
            "room": 101,
            "obj2": {"actor": 3},
            "obj": {"room": 101, "name": "widget"},
            "verb": "give",
        },
        {"verb": "walk_to", "obj": {"room": 101, "name": "door"}},  # no room -> key omitted
        {"choose": ["b"], "until": [{"has": 500}]},
    )
    assert list(out[0]) == C4_KEYS
    assert list(out[1]) == [k for k in C4_KEYS if k != "room"]
    assert list(out[2]) == ["action", "choose", "until"]
    for step in out:
        _assert_c4(step)


# --- steps.toml and JSONL ----------------------------------------------------


def test_write_jsonl_round_trips(index, tmp_path):
    out = _compile_one(
        index,
        {"verb": "give", "obj": {"room": 101, "name": "widget"}, "obj2": {"actor": 3}, "room": 102},
        {"choose": ["yes, please"], "until": [{"not": {"bit": 7, "eq": 0}}]},
    )
    path = tmp_path / "nested" / "dir" / "plan.jsonl"
    write_jsonl(out, path)
    text = path.read_text()
    assert text.endswith("\n")
    lines = text.splitlines()
    assert len(lines) == len(out)
    for line, step in zip(lines, out):
        assert line == json.dumps(step, separators=(",", ":"))
        parsed = json.loads(line)
        assert parsed == step
        assert list(parsed) == list(step)


def test_write_jsonl_empty(tmp_path):
    path = tmp_path / "empty.jsonl"
    write_jsonl([], path)
    assert path.read_text() == ""


def test_load_steps_rejects_malformed_toml(tmp_path):
    bad = tmp_path / "steps.toml"
    bad.write_text("[actions\n")
    with pytest.raises(TemplateError):
        load_steps(bad)


def test_toy_end_to_end(index, tmp_path):
    steps = load_steps(TOY_STEPS)
    plan = _plan(
        "take-widget", "open-crate", "walk workshop office", "buy-ledger", "answer-clerk", "give-widget-clerk"
    )
    out = compile_plan(plan, steps, index)
    assert out == [
        {"action": "take-widget", "verb": PICK_UP, "obj": 500, "obj2": 0, "room": 101, "choose": [], "until": []},
        {"action": "open-crate", "verb": PICK_UP, "obj": 503, "obj2": 0, "room": 101, "choose": [], "until": []},
        {"action": "walk workshop office", "verb": WALK_TO, "obj": 501, "obj2": 0, "room": 101, "choose": [],
         "until": []},
        {"action": "buy-ledger", "verb": PICK_UP, "obj": 512, "obj2": 0, "room": 102, "choose": [], "until": []},
        {"action": "buy-ledger", "verb": TALK_TO, "obj": 511, "obj2": 0, "room": 102, "choose": ["ledger", "yes"],
         "until": []},
        {"action": "answer-clerk", "choose": ["goodbye"], "until": []},
        {"action": "give-widget-clerk", "verb": GIVE, "obj": 500, "obj2": 3, "room": 102, "choose": [],
         "until": [{"var": 20, "eq": 0}, {"not": {"bit": 7, "eq": 0}}]},
    ]
    for step in out:
        _assert_c4(step)

    path = tmp_path / "plans" / "toy.jsonl"
    write_jsonl(out, path)
    parsed = [json.loads(line) for line in path.read_text().splitlines()]
    assert parsed == out
