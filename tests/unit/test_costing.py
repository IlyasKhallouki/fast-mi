"""Unit tests for ``speedrun.costing``: timed domain/problem copies and the measured cost table.

The ``requires_fd`` tests run the real Fast Downward on the timed copies: a
toy whose optimal plan changes with measured costs, and the real Part I
model (read only, copied to tmp) with an empty cost table, which must plan
exactly like the untimed model.
"""

import json
import re

import pytest

from speedrun import costing, paths
from speedrun.planner import parse_plan, run_planner

DOMAIN = """\
;; Toy domain for the costing tests. Comments carry parens: loadRoomWithEgo(426,33).
(define (domain toy-rooms)
  (:requirements :strips :typing :negative-preconditions :action-costs)
  (:types room item)
  (:constants dock bar kitchen - room meat - item)
  (:predicates
    (at ?r - room)                    ; ego's room (not (a fluent))
    (link ?from ?to - room)           ; static exit
    (has ?i - item)
    (door-open))
  (:functions (total-cost) - number)

  ; src: data/scripts/global/script-002.txt [02DB] — walk(ego) to the exit (see [039D])
  (:action walk
    :parameters (?from ?to - room)
    :precondition (and (at ?from) (link ?from ?to))
    :effect (and (not (at ?from)) (at ?to) (increase (total-cost) 1)))

  ; src: data/scripts/room-033-dock/obj-0428-door.txt [0029] — Open 428 (state 1)
  (:action open-door
    :parameters ()
    :precondition (and (at dock) (not (door-open)))
    :effect (and (door-open) (increase (total-cost) 1)))

  ; src: data/scripts/room-041-kitchen/obj-0566-hunk-of-meat.txt [0035] — Pick up 566 (owner 15)
  (:action pick-up-meat
    :parameters ()
    :precondition (and (at kitchen) (not (has meat)))
    :effect (and (has meat) (increase (total-cost) 1))))
"""

PROBLEM = """\
;; Toy problem (comments with parens: (link dock bar) is cited below).
(define (problem toy-rooms-1)
  (:domain toy-rooms)
  (:init
    (at dock)
    (= (total-cost) 0)
    (link dock bar) ; src: data/scripts/room-033-dock/obj-0428-door.txt [0035] — loadRoomWithEgo(315,28)
    (link bar dock) ; src: data/scripts/room-028-bar/obj-0315-door.txt [0072] — (state 1)
    (link bar kitchen) ; src: data/scripts/room-028-bar/local-218.txt [0017] — loadRoomWithEgo(570,41)
    (link kitchen bar)) ; src: data/scripts/room-041-kitchen/obj-0570-door.txt [003C]
  (:goal (and (has meat) (door-open)))
  (:metric minimize (total-cost)))
"""

LINKS = [("dock", "bar"), ("bar", "dock"), ("bar", "kitchen"), ("kitchen", "bar")]


def _comments(text: str) -> list[str]:
    return [line[line.index(";"):] for line in text.splitlines() if ";" in line]


# --- integer costs -----------------------------------------------------------------


@pytest.mark.parametrize(("mean", "cost"), [(354.4, 354), (354.6, 355), (0, 1), (0.3, 1), (1, 1), (9492, 9492)])
def test_integer_cost_is_rounded_and_at_least_1(mean, cost):
    assert costing.integer_cost(mean) == cost


# --- apply_costs: 0-ary actions -----------------------------------------------------


def test_zero_ary_costs_become_measured_ticks():
    domain, problem = costing.apply_costs(DOMAIN, PROBLEM, {"open-door": 354.4, "pick-up-meat": 0.2})
    assert "(door-open) (increase (total-cost) 354))" in domain
    costs = costing.ground_costs(domain, problem)
    assert costs["open-door"] == 354
    assert costs["pick-up-meat"] == 1  # a 0-tick action still costs 1


def test_unmeasured_actions_get_the_default_cost():
    domain, problem = costing.apply_costs(DOMAIN, PROBLEM, {"open-door": 50}, default_cost=7)
    costs = costing.ground_costs(domain, problem)
    assert costs["open-door"] == 50
    assert costs["pick-up-meat"] == 7
    assert {costs[f"walk {a} {b}"] for a, b in LINKS} == {7}


def test_costs_accept_cost_table_entries():
    entries = {"open-door": {"mean": 12.4, "n": 3}, "walk dock bar": {"mean": 99.5, "n": 5}}
    costs = costing.ground_costs(*costing.apply_costs(DOMAIN, PROBLEM, entries))
    assert costs["open-door"] == 12 and costs["walk dock bar"] == 100


@pytest.mark.parametrize("default", [0, -1, 1.5])
def test_default_cost_must_be_a_positive_integer(default):
    with pytest.raises(ValueError):
        costing.apply_costs(DOMAIN, PROBLEM, {}, default_cost=default)


# --- apply_costs: walk -------------------------------------------------------------


def test_walk_cost_is_a_static_function_with_one_value_per_link():
    domain, problem = costing.apply_costs(DOMAIN, PROBLEM, {"walk bar kitchen": 120.6, "walk dock bar": 40})
    assert "(increase (total-cost) (walk-cost ?from ?to))" in domain
    assert re.search(r"\(:functions \(total-cost\) - number\s+\(walk-cost \?from \?to - room\) - number\)", domain)
    values = re.findall(r"\(= \(walk-cost (\S+) (\S+)\) (\d+)\)", problem)
    assert values == [("dock", "bar", "40"), ("bar", "dock", "1"), ("bar", "kitchen", "121"), ("kitchen", "bar", "1")]
    costs = costing.ground_costs(domain, problem)
    assert {k: v for k, v in costs.items() if k.startswith("walk ")} == {
        "walk dock bar": 40, "walk bar dock": 1, "walk bar kitchen": 121, "walk kitchen bar": 1,
    }  # fmt: skip


def test_values_open_the_init_section_on_their_own_lines():
    _, problem = costing.apply_costs(DOMAIN, PROBLEM, {})
    init = problem[problem.index("(:init"): problem.index("(:goal")]
    assert init.count("(= (walk-cost") == len(LINKS)
    lines = init.splitlines()
    assert lines[0].strip() == "(:init"
    assert all(line.strip().startswith(("(= (walk-cost", ";;")) for line in lines[1:6])


def test_init_on_one_line_with_facts_still_parses():
    problem = PROBLEM.replace("(:init\n    (at dock)", "(:init (at dock)")
    timed = costing.apply_costs(DOMAIN, problem, {"walk dock bar": 4})
    assert costing.ground_costs(*timed)["walk dock bar"] == 4


def test_comments_and_citations_are_preserved():
    domain, problem = costing.apply_costs(DOMAIN, PROBLEM, {"open-door": 5, "walk dock bar": 9})
    for comment in _comments(DOMAIN):
        assert comment in domain
    for comment in _comments(PROBLEM):
        assert comment in problem
    # Every problem line survives verbatim (citations stay on their link lines), and so does
    # every domain line except the cost terms and the :functions declaration.
    out_problem, out_domain = set(problem.splitlines()), set(domain.splitlines())
    assert [line for line in PROBLEM.splitlines() if line not in out_problem] == []
    changed = [line for line in DOMAIN.splitlines() if line not in out_domain]
    assert changed and all("(increase (total-cost)" in line or "(:functions" in line for line in changed)


def test_timed_copy_carries_a_header():
    domain, problem = costing.apply_costs(DOMAIN, PROBLEM, {})
    assert domain.startswith(";; TIMED COPY")
    assert problem.startswith(";; TIMED COPY")


# --- apply_costs: generic parameterised actions ------------------------------------


GENERIC_DOMAIN = """\
(define (domain shop)
  (:requirements :strips :typing :action-costs)
  (:types item shop)
  (:predicates (at-shop ?s - shop) (sells ?s - shop ?i - item) (has ?i - item) (open ?s - shop))
  (:functions (total-cost) - number)
  (:action buy
    :parameters (?i - item ?s - shop)
    :precondition (and (at-shop ?s) (open ?s) (sells ?s ?i) (not (has ?i)))
    :effect (and (has ?i) (increase (total-cost) 1))))
"""

GENERIC_PROBLEM = """\
(define (problem shop-1)
  (:domain shop)
  (:objects map shovel - item store voodoo - shop)
  (:init (at-shop store) (open store) (open voodoo)
         (sells store map) (sells store shovel) (sells voodoo map)
         (= (total-cost) 0))
  (:goal (has map))
  (:metric minimize (total-cost)))
"""


def test_any_parameterised_action_gets_its_own_cost_function():
    domain, problem = costing.apply_costs(GENERIC_DOMAIN, GENERIC_PROBLEM, {"buy map store": 30})
    assert "(increase (total-cost) (buy-cost ?i ?s))" in domain
    assert "(buy-cost ?i - item ?s - shop) - number" in domain
    costs = costing.ground_costs(domain, problem)
    # Ground instances come from the join of the static preconditions: nothing changes
    # at-shop, open or sells, and only the store's two items pass all three.
    assert costs == {"buy map store": 30, "buy shovel store": 1}
    assert problem.count("(= (buy-cost ") == 2


def test_a_parameter_no_static_precondition_binds_fails_loudly():
    drop = """
  (:action drop
    :parameters (?i - item)
    :precondition (has ?i)
    :effect (and (not (has ?i)) (increase (total-cost) 1))))
"""
    domain = GENERIC_DOMAIN.rstrip().removesuffix(")") + drop
    with pytest.raises(costing.CostingError, match=r"drop.*\?i"):
        costing.apply_costs(domain, GENERIC_PROBLEM, {})


def test_an_action_without_a_cost_fails_loudly():
    domain = DOMAIN.replace("(door-open) (increase (total-cost) 1)", "(door-open)")
    with pytest.raises(costing.CostingError, match="open-door"):
        costing.apply_costs(domain, PROBLEM, {})


def test_a_cost_that_is_already_a_function_fails_loudly():
    domain, problem = costing.apply_costs(DOMAIN, PROBLEM, {})
    with pytest.raises(costing.CostingError, match="walk"):
        costing.apply_costs(domain, problem, {})


def test_a_problem_without_metric_fails_loudly():
    with pytest.raises(costing.CostingError, match="metric"):
        costing.apply_costs(DOMAIN, PROBLEM.replace("(:metric minimize (total-cost))", ""), {})


def test_unbalanced_pddl_fails_loudly():
    with pytest.raises(costing.CostingError):
        costing.apply_costs(DOMAIN + ")", PROBLEM, {})


def test_parens_in_comments_do_not_confuse_the_parser():
    domain = DOMAIN.replace("(:functions", "; a comment with an unbalanced ( paren\n  (:functions")
    problem = PROBLEM.replace("(:goal", "; and a closing ) one\n  (:goal")
    assert costing.ground_costs(*costing.apply_costs(domain, problem, {"open-door": 3}))["open-door"] == 3


def test_write_timed(tmp_path):
    (tmp_path / "domain.pddl").write_text(DOMAIN)
    (tmp_path / "problem.pddl").write_text(PROBLEM)
    domain, problem = costing.write_timed(
        tmp_path / "domain.pddl", tmp_path / "problem.pddl", {"open-door": 8}, tmp_path / "timed"
    )
    assert (domain, problem) == (tmp_path / "timed" / "domain.pddl", tmp_path / "timed" / "problem.pddl")
    assert costing.ground_costs(domain.read_text(), problem.read_text())["open-door"] == 8


# --- cost table --------------------------------------------------------------------


def _summary(runs: list[list[tuple[str, int]]], skips: bool = True, failed: int = 0, talkspeed: int = 255) -> dict:
    out = []
    for seed, instances in enumerate(runs, 1):
        out.append({"seed": seed, "ok": True, "bridge": "speedrun-bridge v1",
                    "instances": [{"action": a, "ticks": t, "index": i} for i, (a, t) in enumerate(instances)]})  # fmt: skip
    for k in range(failed):
        out.append({"seed": 100 + k, "ok": False, "instances": [], "bridge": None})
    return {"version": 1, "skips": {"text": skips, "cutscenes": skips}, "engine": {"talkspeed": talkspeed},
            "runs": out}


def test_cost_table_pools_samples_from_several_summaries():
    a = _summary([[("open-door", 10), ("walk dock bar", 40)], [("open-door", 12), ("walk dock bar", 44)]])
    b = _summary([[("open-door", 14), ("pick-up-meat", 7)]], failed=1)
    table = costing.CostTable.from_summaries([a, b])
    assert table.samples("open-door") == [10, 12, 14]
    assert table.measured("walk dock bar") and not table.measured("walk bar dock")
    entry = table.entry("open-door")
    assert (entry["n"], entry["mean"], entry["min"], entry["max"], entry["cost"]) == (3, 12.0, 10, 14, 12)
    assert entry["stdev"] == pytest.approx(2.0)
    assert table.means() == {"open-door": 12.0, "walk dock bar": 42.0, "pick-up-meat": 7.0}


def test_cost_table_refuses_to_mix_skip_settings():
    table = costing.CostTable.from_summaries([_summary([[("open-door", 10)]], skips=True)])
    with pytest.raises(costing.CostingError, match="skip"):
        table.add_summary(_summary([[("open-door", 10)]], skips=False))


def test_cost_table_refuses_to_mix_engine_settings():
    table = costing.CostTable.from_summaries([_summary([[("open-door", 10)]], talkspeed=255)])
    assert table.engine == {"talkspeed": 255}
    with pytest.raises(costing.CostingError, match="talkspeed"):
        table.add_summary(_summary([[("open-door", 10)]], talkspeed=60))


def test_cost_table_round_trips_through_json(tmp_path):
    table = costing.CostTable.from_summaries([_summary([[("open-door", 10), ("walk dock bar", 41)]])])
    path = tmp_path / "measured-costs.json"
    table.save(path)
    data = json.loads(path.read_text())
    assert data["version"] == costing.TABLE_VERSION and data["unit"] == "ticks"
    assert data["actions"]["walk dock bar"]["n"] == 1 and data["actions"]["walk dock bar"]["samples"] == [41]
    assert data["skips"] == {"text": True, "cutscenes": True}
    assert data["engine"] == {"talkspeed": 255}
    loaded = costing.CostTable.load(path)
    assert loaded.to_json() == table.to_json()
    # One action per line, so diffs of the committed table stay readable.
    assert sum(1 for line in path.read_text().splitlines() if '"samples"' in line) == 2


def test_cost_table_feeds_apply_costs():
    table = costing.CostTable.from_summaries([_summary([[("open-door", 10), ("walk dock bar", 41)]])])
    costs = costing.ground_costs(*costing.apply_costs(DOMAIN, PROBLEM, table.means()))
    assert costs["open-door"] == 10 and costs["walk dock bar"] == 41 and costs["walk bar dock"] == 1


# --- Fast Downward ---------------------------------------------------------------------

TOY_DOMAIN = paths.ROOT / "tests" / "fixtures" / "pddl" / "toy-domain.pddl"
TOY_PROBLEM = paths.ROOT / "tests" / "fixtures" / "pddl" / "toy-problem.pddl"


def _plan(tmp_path, name, domain_text, problem_text):
    d, p = tmp_path / f"{name}-domain.pddl", tmp_path / f"{name}-problem.pddl"
    d.write_text(domain_text)
    p.write_text(problem_text)
    return run_planner(d, p, tmp_path / f"{name}.sas_plan")


@pytest.mark.requires_fd
def test_measured_costs_change_the_optimal_plan(fd_ready, tmp_path):
    # The toy: (drive a d) costs 10, three walks cost 1 each, so the unit plan walks.
    domain, problem = TOY_DOMAIN.read_text(), TOY_PROBLEM.read_text()
    walk = _plan(tmp_path, "unit", domain, problem)
    assert walk.actions == [("walk", "a", "b"), ("walk", "b", "c"), ("walk", "c", "d")]

    # Measured: driving takes 40 ticks, each walk 20, so driving is faster.
    measured = {"drive a d": 40, "walk a b": 20, "walk b c": 20, "walk c d": 20}
    timed = _plan(tmp_path, "timed", *costing.apply_costs(domain, problem, measured))
    assert timed.actions == [("drive", "a", "d")]
    assert timed.cost == 40

    # And with slower driving the walks win again, at the measured total.
    slower = {**measured, "drive a d": 61}
    again = _plan(tmp_path, "slower", *costing.apply_costs(domain, problem, slower))
    assert again.actions == walk.actions and again.cost == 60


@pytest.mark.requires_fd
def test_toy_rooms_timed_copy_plans_with_fd(fd_ready, tmp_path):
    plan = _plan(tmp_path, "rooms", *costing.apply_costs(DOMAIN, PROBLEM, {"open-door": 30, "walk bar kitchen": 5}))
    assert plan.actions == [("open-door",), ("walk", "dock", "bar"), ("walk", "bar", "kitchen"), ("pick-up-meat",)]
    assert plan.cost == 30 + 1 + 5 + 1


@pytest.mark.requires_fd
def test_real_model_with_no_measurements_plans_like_the_unit_model(fd_ready, tmp_path):
    # FD silently drops a ground action whose cost function has no :init value, so a
    # missing (= (walk-cost a b) N) would quietly remove that exit. With every cost at 1
    # the timed copy must plan exactly like the untimed model.
    seg = paths.PDDL_DIR / "part1"
    domain, problem = (seg / "domain.pddl").read_text(), (seg / "problem.pddl").read_text()
    unit = _plan(tmp_path, "unit", domain, problem)
    timed_domain, timed_problem = costing.apply_costs(domain, problem, {})
    links = len(re.findall(r"^\s*\(link \S+ \S+\)", problem, re.MULTILINE))
    assert timed_problem.count("(= (walk-cost ") == links
    timed = _plan(tmp_path, "timed", timed_domain, timed_problem)
    assert timed.cost == unit.cost
    assert timed.actions == unit.actions


def test_parse_plan_of_timed_trailer_is_general_cost():
    assert parse_plan("(drive a d)\n; cost = 40 (general cost)\n").cost == 40
