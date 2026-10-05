"""Merging extracted fragments into one model (``speedrun.extract``) and compiling its plans to C4 steps."""

import re

import pytest
from _extract_toy import FRAGMENTS, GOAL, HALL, HALL_ACTIONS, YARD, YARD_ACTIONS, action, state_dump

from speedrun.citations import parse_sexp
from speedrun.compiler import C4_KEYS
from speedrun.extract import (
    ExtractError,
    compile_extracted,
    goal_literals,
    load_fragments,
    merge,
)
from speedrun.planner import Plan, run_planner


def _section(tree: list, key: str) -> list:
    return next(item for item in tree if isinstance(item, list) and item and item[0] == key)


def _init(problem: str) -> list[str]:
    (tree,) = parse_sexp(problem)
    return [" ".join(f) if f[0] != "=" else "=" for f in _section(tree, ":init")[1:]]


# --- merge: the domain --------------------------------------------------------------------


def test_domain_has_every_action_and_the_lmcut_subset():
    domain, _ = merge(FRAGMENTS, state_dump(), GOAL)
    (tree,) = parse_sexp(domain)
    assert tree[:2] == ["define", ["domain", "extracted"]]
    assert _section(tree, ":requirements")[1:] == [":strips", ":negative-preconditions", ":action-costs"]
    assert _section(tree, ":functions")[1:] == [["total-cost"], "-", "number"]
    names = [item[1] for item in tree if isinstance(item, list) and item and item[0] == ":action"]
    assert names == YARD_ACTIONS + HALL_ACTIONS


def test_domain_keeps_the_annotations():
    domain, _ = merge(FRAGMENTS, state_dump(), GOAL)
    assert "; src: data/scripts/room-091-hall/obj-0902-chest.txt [0015] — sets Bit[85]" in domain
    assert "; dialogue: yes please" in domain


def test_predicates_are_collected_from_usage_and_the_goal():
    domain, _ = merge(FRAGMENTS, state_dump(), GOAL + [{"bit": 99, "eq": 0}])
    (tree,) = parse_sexp(domain)
    predicates = [p[0] for p in _section(tree, ":predicates")[1:]]
    assert all(len(p) == 1 for p in _section(tree, ":predicates")[1:])  # 0-ary
    assert len(predicates) == len(set(predicates))
    assert set(predicates) == {
        "at-r90", "at-r91", "at-r92", "has-o902", "has-o904", "bit-85", "bit-86", "bit-99",
        "state-o901-0", "state-o901-1", "owner-o904-15", "class-o905-6",
        "var-195-ge-100", "var-54-eq--80", "var-300-eq-1",
    }  # fmt: skip
    # Grouped by kind, then by number, so related atoms sit together.
    assert predicates.index("at-r90") < predicates.index("at-r91") < predicates.index("at-r92")
    assert predicates.index("bit-85") < predicates.index("bit-86") < predicates.index("bit-99")


def test_domain_name_is_configurable():
    domain, problem = merge(FRAGMENTS, state_dump(), GOAL, name="part1-extracted")
    assert "(domain part1-extracted)" in domain
    assert "(:domain part1-extracted)" in problem


def test_merge_accepts_a_list_of_texts():
    domain, _ = merge([YARD, HALL], state_dump(), GOAL)
    assert "walk-hall-to-cellar" in domain


def test_merge_refuses_invalid_actions():
    with pytest.raises(ExtractError, match="no-cost"):
        merge([action("costless", eff="(and (state-o901-1))")], state_dump(), GOAL)


def test_merge_refuses_duplicate_names():
    with pytest.raises(ExtractError, match="duplicate-name"):
        merge({"a.pddl": action("same"), "b.pddl": action("same")}, state_dump(), GOAL)


def test_merge_refuses_no_actions():
    with pytest.raises(ExtractError, match="no actions"):
        merge({"a.pddl": ""}, state_dump(), GOAL)


# --- merge: the problem ----------------------------------------------------------------------


def test_init_comes_from_the_state_dump():
    state = state_dump(inventory=[902])
    state["vars"][195] = 478
    state["vars"][300] = 1
    state["states"]["901"] = 1
    _, problem = merge(FRAGMENTS, state, GOAL)
    init = _init(problem)
    assert sorted(f for f in init if f != "=") == sorted([
        "at-r90",  # room 90
        "has-o902",  # inventory
        "state-o901-1",  # states["901"] == 1
        "owner-o904-15",  # owners["904"] == 15
        "class-o905-6",  # classes["905"] == [6]
        "var-195-ge-100",  # 478 >= 100
        "var-54-eq--80",  # vars[54] == -80
        "var-300-eq-1",
    ])  # fmt: skip
    assert "=" in init
    assert re.search(r"\(=\s*\(total-cost\)\s+0\)", problem)


def test_init_holds_only_atoms_the_domain_mentions():
    state = state_dump()  # bits 116 and 395 are set, room 90
    _, problem = merge(FRAGMENTS, state, GOAL)
    assert "bit-116" not in problem and "bit-395" not in problem
    assert "(bit-85)" not in _init(problem)


def test_ge_threshold_is_inclusive_and_below_is_false():
    state = state_dump()
    state["vars"][195] = 100
    assert "var-195-ge-100" in _init(merge(FRAGMENTS, state, GOAL)[1])
    state["vars"][195] = 99
    assert "var-195-ge-100" not in _init(merge(FRAGMENTS, state, GOAL)[1])


def test_eq_atoms_other_than_the_value_are_false():
    state = state_dump()
    state["vars"][54] = 0
    assert "var-54-eq--80" not in _init(merge(FRAGMENTS, state, GOAL)[1])


def test_unknown_object_in_the_dump_is_an_error():
    frag = action("a", pre="(and (at-r90) (state-o999-0))")
    with pytest.raises(ExtractError, match="999"):
        merge([frag], state_dump(), GOAL)


def test_var_outside_the_dump_is_an_error():
    frag = action("a", pre="(and (at-r90) (var-900-eq-1))")
    with pytest.raises(ExtractError, match="900"):
        merge([frag], state_dump(), GOAL)


def test_state_dump_from_a_path(tmp_path):
    import json

    path = tmp_path / "state-start.json"
    path.write_text(json.dumps(state_dump()))
    _, problem = merge(FRAGMENTS, path, GOAL)
    assert "at-r90" in _init(problem)


def test_goal_and_metric():
    _, problem = merge(FRAGMENTS, state_dump(), GOAL)
    (tree,) = parse_sexp(problem)
    assert _section(tree, ":goal")[1] == ["and", ["bit-85"], ["bit-86"]]
    assert _section(tree, ":metric")[1:] == ["minimize", ["total-cost"]]


def test_goal_literals_from_c3():
    assert goal_literals(GOAL) == [(True, "bit-85"), (True, "bit-86")]
    assert goal_literals([
        {"bit": 7, "eq": 0},
        {"not": {"bit": 8, "eq": 1}},
        {"var": 195, "eq": 3},
        {"room": 33},
        {"has": 316},
        {"owner": 316, "eq": 15},
        {"state": 316, "eq": 1},
        {"not": {"not": {"room": 41}}},
    ]) == [
        (False, "bit-7"),
        (False, "bit-8"),
        (True, "var-195-eq-3"),
        (True, "at-r33"),
        (True, "has-o316"),
        (True, "owner-o316-15"),
        (True, "state-o316-1"),
        (True, "at-r41"),
    ]  # fmt: skip


@pytest.mark.parametrize(
    "condition", [{"actor_x": 6, "le": 310}, {"bit": 85, "eq": 2}, {"state": 316, "eq": 16}, {"var": 1}]
)
def test_goal_without_a_vocabulary_atom_is_an_error(condition):
    with pytest.raises(ExtractError):
        goal_literals([condition])


# --- load_fragments ----------------------------------------------------------------------------


def test_load_fragments_skips_the_merged_model(tmp_path):
    for name in ("b.pddl", "a.pddl", "domain.pddl", "problem.pddl"):
        (tmp_path / name).write_text(f"; {name}\n")
    (tmp_path / "rejected.json").write_text("[]")
    assert list(load_fragments(tmp_path)) == ["a.pddl", "b.pddl"]
    assert load_fragments(tmp_path)["a.pddl"] == "; a.pddl\n"


def test_load_fragments_of_a_missing_dir_is_empty(tmp_path):
    assert load_fragments(tmp_path / "nope") == {}


# --- compile_extracted ---------------------------------------------------------------------------


def _plan(*names: str) -> Plan:
    return Plan(actions=[(n,) for n in names], cost=len(names))


def test_sentence_actions_compile_to_c4_steps():
    steps = compile_extracted(_plan("open-door", "take-chest", "give-coin-to-statue"), FRAGMENTS)
    assert steps == [
        {"action": "open-door", "verb": 2, "obj": 901, "obj2": 0, "room": 90, "choose": [], "until": []},
        {"action": "take-chest", "verb": 9, "obj": 902, "obj2": 0, "room": 91, "choose": ["yes please", "thanks"],
         "until": []},
        {"action": "give-coin-to-statue", "verb": 4, "obj": 904, "obj2": 905, "room": 91, "choose": [],
         "until": []},
    ]  # fmt: skip


def test_click_actions_compile_to_click_entries():
    (step,) = compile_extracted(_plan("wave-coin"), FRAGMENTS)
    assert step == {
        "action": "wave-coin",
        "room": 91,
        "click": [{"verb": 7}, {"inventory": 904, "offset": -1}],
        "choose": [],
        "until": [],
    }
    no_offset = action("poke", inputs=("; click: 7,inv:904",))
    (step,) = compile_extracted(_plan("poke"), [no_offset])
    assert step["click"] == [{"verb": 7}, {"inventory": 904}]


def test_forest_steps_wait_on_var_4_instead_of_a_room_check():
    frag = action("walk-215-203", room="; room: 215", pre="(and (at-r215))", inputs=("; sentence: 11 685",))
    (step,) = compile_extracted(_plan("walk-215-203"), [frag])
    assert "room" not in step
    assert step["until"] == [{"var": 4, "eq": 215}]


def test_steps_keep_the_c4_key_order():
    for step in compile_extracted(_plan("wave-coin", "take-chest"), FRAGMENTS):
        assert list(step) == [k for k in C4_KEYS if k in step]


def test_plan_names_are_matched_case_insensitively():
    (step,) = compile_extracted(Plan(actions=[("OPEN-DOOR",)], cost=1), FRAGMENTS)
    assert step["action"] == "open-door"


def test_unknown_plan_action_is_an_error():
    with pytest.raises(ExtractError, match="no-such-action"):
        compile_extracted(_plan("no-such-action"), FRAGMENTS)


def test_plan_action_with_arguments_is_an_error():
    with pytest.raises(ExtractError, match="walk dock lookout"):
        compile_extracted(Plan(actions=[("walk", "dock", "lookout")], cost=1), FRAGMENTS)


# --- the real planner -------------------------------------------------------------------------------


@pytest.mark.requires_fd
def test_merged_toy_model_is_solvable(fd_ready, tmp_path):
    domain, problem = merge(FRAGMENTS, state_dump(), GOAL)
    (tmp_path / "domain.pddl").write_text(domain)
    (tmp_path / "problem.pddl").write_text(problem)
    plan = run_planner(tmp_path / "domain.pddl", tmp_path / "problem.pddl", tmp_path / "toy.sas_plan",
                       time_limit_s=60, memory_limit="2G")  # fmt: skip
    names = [a[0] for a in plan.actions]
    # Coin and door first (either order), into the hall, then chest and statue (either order).
    assert sorted(names[:2]) == ["open-door", "pick-up-coin"]
    assert names[2] == "walk-yard-to-hall"
    assert sorted(names[3:]) == ["give-coin-to-statue", "take-chest"]  # take-chest needs var-54-eq--80
    assert plan.cost == 5
    steps = compile_extracted(plan, FRAGMENTS)
    assert [s["action"] for s in steps] == names
