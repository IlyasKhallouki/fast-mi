"""Unit tests for ``speedrun.keyed``: the position-keyed timed domain.

Every action that runs in a keyed room reads ego's position token through a
``?ctx - pos`` parameter and pays ``(<action>-cost ?ctx ...)``; actions that
move him set ``(ego-pos <anchor>)``. The ``requires_fd`` tests run Fast
Downward: with every cost at 1 the keyed model must plan exactly like the
unkeyed one (on a toy and on the real Part I model), and on the ``hall`` toy
keyed costs find the truly fastest order where pooled means do not.
"""

import re
import tomllib

import pytest
from test_positions import TOWN_DOMAIN, TOWN_OBJECTS, TOWN_PROBLEM, town_steps

from speedrun import costing, paths
from speedrun.compiler import ObjectIndex
from speedrun.costing import ANY, CostTable
from speedrun.keyed import apply_keyed_costs, keyed_model
from speedrun.planner import Plan, run_planner
from speedrun.positions import START, derive_positions, pddl_name


@pytest.fixture
def town():
    return derive_positions(TOWN_DOMAIN, TOWN_PROBLEM, town_steps(), ObjectIndex.from_dict(TOWN_OBJECTS))


def _ground(model) -> set[str]:
    return set(costing.ground_costs(model.domain, model.problem))


def _action_text(domain: str, name: str) -> str:
    start = domain.index(f"(:action {name}\n")
    end = domain.find("(:action ", start + 1)
    return domain[start : end if end != -1 else len(domain)]


# --- structure ---------------------------------------------------------------------------


def test_full_keying_declares_positions(town):
    model = keyed_model(TOWN_DOMAIN, TOWN_PROBLEM, town)
    assert re.search(r"\(:types room pos\)", model.domain)
    for token in town.tokens():
        assert pddl_name(token) in model.domain
    assert re.search(r"- pos\s*\)", model.domain)
    for decl in ("(ego-pos ?p - pos)", "(pos-in-room ?p - pos ?r - room)", "(link-entry ?from ?to - room ?p - pos)"):
        assert decl in model.domain
    assert f"(ego-pos {pddl_name(START)})" in model.problem
    assert f"(pos-in-room {pddl_name('entry:street:shop:501')} shop)" in model.problem
    assert f"(link-entry street yard {pddl_name('entry:street:yard:504')})" in model.problem
    assert ANY not in {model.names[n] for n in model.names}  # nothing is unkeyed


def test_full_keying_grounds_one_instance_per_context(town):
    model = keyed_model(TOWN_DOMAIN, TOWN_PROBLEM, town)
    ground = _ground(model)
    street = {pddl_name(t) for t in town.tokens_in("street")}
    assert {g for g in ground if g.startswith("open-door")} == {f"open-door {t}" for t in street}
    assert {g for g in ground if g.startswith("walk street yard")} == {
        f"walk street yard {t} {pddl_name('entry:street:yard:504')}" for t in street
    }
    assert "polish-coin" in ground  # room-agnostic: never keyed
    shop = {pddl_name(t) for t in town.tokens_in("shop")}
    assert {g for g in ground if g.startswith("buy-key")} == {f"buy-key {t}" for t in shop}


def test_actions_read_and_set_the_position(town):
    model = keyed_model(TOWN_DOMAIN, TOWN_PROBLEM, town)
    walk = _action_text(model.domain, "walk")
    assert "(ego-pos ?ctx) (pos-in-room ?ctx ?from) (link-entry ?from ?to ?next)" in walk
    assert "(not (ego-pos ?ctx)) (ego-pos ?next)" in walk
    opened = _action_text(model.domain, "open-door")
    assert ":parameters (?ctx - pos)" in opened
    assert "(ego-pos ?ctx) (pos-in-room ?ctx street)" in opened
    assert f"(not (ego-pos ?ctx)) (ego-pos {pddl_name('obj:street:501')})" in opened
    into_shop = _action_text(model.domain, "walk-into-shop")
    assert f"(ego-pos {pddl_name('entry:street:shop:501')})" in into_shop
    # Unchanged position: reads the context, sets nothing.
    answer = _action_text(model.domain, "answer-clerk")
    assert "(pos-in-room ?ctx shop)" in answer and "(not (ego-pos" not in answer
    assert "ego-pos" not in _action_text(model.domain, "polish-coin")
    # Still the lmcut-safe subset: no conditional effects or quantifiers.
    assert not re.search(r"\((when|forall|exists|or|imply)\b", model.domain)


def test_selective_keying_gives_unkeyed_rooms_one_shared_context(town):
    model = keyed_model(TOWN_DOMAIN, TOWN_PROBLEM, town, keyed_rooms={"shop"})
    ground = _ground(model)
    any_ = pddl_name(ANY)
    assert f"(ego-pos {any_})" in model.problem  # the street is not keyed
    assert "open-door" in ground  # an unkeyed room's action: no context parameter
    assert "walk-into-shop" in ground
    into_shop = _action_text(model.domain, "walk-into-shop")
    assert f"(ego-pos {any_})" in into_shop and f"(ego-pos {pddl_name('entry:street:shop:501')})" in into_shop
    assert {g for g in ground if g.startswith("walk street yard")} == {f"walk street yard {any_} {any_}"}
    assert {g for g in ground if g.startswith("walk shop street")} == {
        f"walk shop street {pddl_name(t)} {any_}" for t in town.tokens_in("shop")
    }
    assert {g for g in ground if g.startswith("buy-key")} == {f"buy-key {pddl_name(t)}" for t in town.tokens_in("shop")}
    assert pddl_name("obj:street:501") not in model.domain


def test_split_and_strip(town):
    model = keyed_model(TOWN_DOMAIN, TOWN_PROBLEM, town, keyed_rooms={"street", "shop"})
    s, e = pddl_name(START), pddl_name("entry:street:yard:504")
    assert model.split(f"walk street yard {s} {e}") == ("walk street yard", START)
    assert model.split(f"open-door {s}") == ("open-door", START)
    assert model.split("polish-coin") == ("polish-coin", None)
    assert model.split(f"walk yard street {pddl_name(ANY)} {pddl_name(ANY)}") == ("walk yard street", ANY)
    plan = Plan(actions=[("open-door", s), ("walk", "street", "yard", s, e), ("polish-coin",)], cost=3)
    assert model.strip(plan).actions == [("open-door",), ("walk", "street", "yard"), ("polish-coin",)]
    assert model.strip(plan).cost == 3


def test_effective_pairs_of_a_plan(town):
    model = keyed_model(TOWN_DOMAIN, TOWN_PROBLEM, town, keyed_rooms={"shop"})
    pairs = model.pairs(["open-door", "walk-into-shop", "buy-key", "walk shop street", "polish-coin"])
    assert pairs == [("open-door", ANY), ("walk-into-shop", ANY), ("buy-key", "entry:street:shop:501"),
                     ("walk shop street", "obj:shop:511"), ("polish-coin", ANY)]  # fmt: skip


def test_a_token_name_colliding_with_a_constant_fails(town):
    domain = TOWN_DOMAIN.replace("street shop yard attic - room", "street shop yard attic p_start - room")
    with pytest.raises(costing.CostingError, match="p_start"):
        keyed_model(domain, TOWN_PROBLEM, town)


# --- costs: every instance valued, no overflow ---------------------------------------------


def _cost(action: str, ctx: str | None) -> float:
    return 10.0 * len(action) + (0 if ctx is None else len(ctx))


def test_every_ground_instance_gets_its_cost(town):
    model = keyed_model(TOWN_DOMAIN, TOWN_PROBLEM, town)
    domain, problem = apply_keyed_costs(model, _cost)
    costs = costing.ground_costs(domain, problem)
    assert set(costs) == _ground(model)
    for ground, value in costs.items():
        assert value == costing.integer_cost(_cost(*model.split(ground))), ground
    assert "(increase (total-cost) (open-door-cost ?ctx))" in domain
    assert problem.count("(= (open-door-cost ") == len(town.tokens_in("street"))


def test_unknown_costs_default_to_1(town):
    model = keyed_model(TOWN_DOMAIN, TOWN_PROBLEM, town)
    costs = costing.ground_costs(*apply_keyed_costs(model, lambda a, c: None))
    assert set(costs.values()) == {1}


def test_a_missing_value_is_caught_not_dropped(town):
    # Fast Downward silently drops a ground action whose cost has no :init value.
    model = keyed_model(TOWN_DOMAIN, TOWN_PROBLEM, town)
    domain, problem = apply_keyed_costs(model, _cost)
    line = next(x for x in problem.splitlines() if "(= (open-door-cost " in x)
    with pytest.raises(costing.CostingError, match="drop"):
        costing.ground_costs(domain, problem.replace(line, ""))


def test_absurd_costs_fail_before_they_overflow_fd(town, monkeypatch):
    model = keyed_model(TOWN_DOMAIN, TOWN_PROBLEM, town)
    with pytest.raises(costing.CostingError, match="overflow"):
        apply_keyed_costs(model, lambda a, c: costing.MAX_ACTION_COST + 1)
    monkeypatch.setattr(costing, "FD_COST_BUDGET", 1000)
    with pytest.raises(costing.CostingError, match="overflow"):
        apply_keyed_costs(model, lambda a, c: 100)


# --- Fast Downward ---------------------------------------------------------------------


def _plan(tmp_path, name, domain_text, problem_text, **kw):
    d, p = tmp_path / f"{name}-domain.pddl", tmp_path / f"{name}-problem.pddl"
    d.write_text(domain_text)
    p.write_text(problem_text)
    return run_planner(d, p, tmp_path / f"{name}.sas_plan", **kw)


def _operators(tmp_path, name) -> int:
    log = (tmp_path / f"{name}.log").read_text()
    return int(re.search(r"Translator operators: (\d+)", log).group(1))


@pytest.mark.requires_fd
@pytest.mark.parametrize("keyed_rooms", [None, {"shop"}, {"street", "yard"}])
def test_toy_keyed_model_at_unit_cost_plans_like_the_model(fd_ready, tmp_path, town, keyed_rooms):
    unit = _plan(tmp_path, "unit", TOWN_DOMAIN, TOWN_PROBLEM)
    model = keyed_model(TOWN_DOMAIN, TOWN_PROBLEM, town, keyed_rooms=keyed_rooms)
    keyed = _plan(tmp_path, "keyed", *apply_keyed_costs(model, lambda a, c: 1))
    assert keyed.cost == unit.cost
    assert town.contexts([" ".join(a) for a in model.strip(keyed).actions])  # a consistent plan


@pytest.mark.requires_fd
@pytest.mark.parametrize("keyed_rooms", [None, {"dock", "high-street-town", "bar-left", "bar-right", "mansion"}])
def test_real_model_keyed_at_unit_cost_plans_like_the_model(fd_ready, tmp_path, keyed_rooms):
    # The equivalence guard: position bookkeeping must not forbid any plan. With every
    # cost at 1, the keyed model's optimum is the unit model's (66 actions).
    objects = paths.ROOT / "out" / "objects.json"
    if not objects.is_file():
        pytest.skip("OBJECT DUMP MISSING: out/objects.json — the keyed equivalence guard did NOT run")
    seg = paths.PDDL_DIR / "part1"
    domain, problem = (seg / "domain.pddl").read_text(), (seg / "problem.pddl").read_text()
    positions = derive_positions(domain, problem, tomllib.loads((seg / "steps.toml").read_text()),
                                 ObjectIndex.from_dump(objects))  # fmt: skip
    unit = _plan(tmp_path, "unit", domain, problem)
    assert unit.cost == 66
    model = keyed_model(domain, problem, positions, keyed_rooms=keyed_rooms)
    timed = _plan(tmp_path, "timed", *apply_keyed_costs(model, lambda a, c: 1))
    assert timed.cost == unit.cost
    positions.contexts([" ".join(a) for a in model.strip(timed).actions])
    # Silent-drop guard at the Fast Downward level: the function-valued model grounds
    # exactly the operators of the same model with constant costs.
    _plan(tmp_path, "constant", model.domain, model.problem, search="lazy_greedy([ff()])")  # only translates
    assert _operators(tmp_path, "timed") == _operators(tmp_path, "constant")


# --- the hall: keying finds the order pooled means cannot see ------------------------------

HALL_DOMAIN = """\
;; Toy hall (src: synthetic): three ways to collect a and b, then leave.
(define (domain hall)
  (:requirements :strips :typing :negative-preconditions :action-costs)
  (:types room)
  (:constants hall out - room)
  (:predicates (at ?r - room) (link ?from ?to - room) (has-a) (has-b))
  (:functions (total-cost) - number)
  (:action walk
    :parameters (?from ?to - room)
    :precondition (and (at ?from) (link ?from ?to))
    :effect (and (not (at ?from)) (at ?to) (increase (total-cost) 1)))
  (:action get-a
    :parameters ()
    :precondition (and (at hall) (not (has-a)))
    :effect (and (has-a) (increase (total-cost) 1)))
  (:action get-b
    :parameters ()
    :precondition (and (at hall) (not (has-b)))
    :effect (and (has-b) (increase (total-cost) 1)))
  (:action get-ab
    :parameters ()
    :precondition (and (at hall) (not (has-a)) (not (has-b)))
    :effect (and (has-a) (has-b) (increase (total-cost) 1))))
"""

HALL_PROBLEM = """\
(define (problem hall-1)
  (:domain hall)
  (:init
    (at hall)
    (link hall out) ; src: synthetic door
    (= (total-cost) 0))
  (:goal (and (has-a) (has-b) (at out)))
  (:metric minimize (total-cost)))
"""

HALL_OBJECTS = {
    "verbs": [{"id": 11, "name": "Walk to"}, {"id": 9, "name": "Pick up"}, {"id": 2, "name": "Open"}],
    "rooms": [{"room": 201, "objects": [{"id": 601, "name": "door"}, {"id": 602, "name": "box"},
                                        {"id": 603, "name": "chest"}, {"id": 604, "name": "cabinet"}]}],
}  # fmt: skip

HALL_STEPS = {
    "verbs": {"walk_to": "Walk to", "pick_up": "Pick up", "open": "Open"},
    "actions": {
        "walk hall out": {"steps": [{"verb": "walk_to", "obj": {"room": 201, "name": "door"}, "room": 201}]},
        "get-a": {"steps": [{"verb": "pick_up", "obj": {"room": 201, "name": "box"}, "room": 201}]},
        "get-b": {"steps": [{"verb": "pick_up", "obj": {"room": 201, "name": "chest"}, "room": 201}]},
        "get-ab": {"steps": [{"verb": "open", "obj": {"room": 201, "name": "cabinet"}, "room": 201}]},
    },
}

BOX, CHEST, CABINET = "obj:hall:602", "obj:hall:603", "obj:hall:604"

# True ticks by (action, position before it). Leaving from the chest is quick, from the box slow.
HALL_TRUTH = {
    ("get-a", START): 120, ("get-a", CHEST): 60,
    ("get-b", START): 60, ("get-b", BOX): 120,
    ("get-ab", START): 170,
    ("walk hall out", BOX): 300, ("walk hall out", CHEST): 30, ("walk hall out", CABINET): 150,
}  # fmt: skip

HALL_ROUTES = {
    "P1": ["get-a", "get-b", "walk hall out"],  # true 120 + 120 + 30 = 270: the fastest
    "P2": ["get-b", "get-a", "walk hall out"],  # true 60 + 60 + 300 = 420
    "P3": ["get-ab", "walk hall out"],  # true 170 + 150 = 320; pooled means make it look cheapest
}


def hall_positions():
    return derive_positions(HALL_DOMAIN, HALL_PROBLEM, HALL_STEPS, ObjectIndex.from_dict(HALL_OBJECTS))


def true_ticks(actions: list[str], positions) -> int:
    return sum(HALL_TRUTH[(a, c)] for a, c in zip(actions, positions.contexts(actions)))


def hall_table(positions) -> CostTable:
    """One measured run of each route, pooled with position contexts."""
    table = CostTable()
    for route in HALL_ROUTES.values():
        contexts = positions.contexts(route)
        instances = [{"action": a, "ticks": HALL_TRUTH[(a, c)], "index": i} for i, (a, c) in
                     enumerate(zip(route, contexts))]  # fmt: skip
        run = {"seed": 1, "ok": True, "bridge": "speedrun-bridge v1", "instances": instances}
        summary = {"skips": None, "engine": None, "actions": route, "runs": [run]}
        table.add_summary(summary, contexts=contexts)
    return table


def test_hall_truth_is_what_the_table_pools():
    positions = hall_positions()
    table = hall_table(positions)
    assert table.mean("walk hall out") == pytest.approx(160.0)  # pooled: (300 + 30 + 150) / 3
    assert table.keyed_cost("walk hall out", CHEST) == 30
    assert {r: true_ticks(a, positions) for r, a in HALL_ROUTES.items()} == {"P1": 270, "P2": 420, "P3": 320}


@pytest.mark.requires_fd
def test_keyed_costs_find_the_truly_fastest_order_pooled_means_do_not(fd_ready, tmp_path):
    positions = hall_positions()
    table = hall_table(positions)
    pooled = _plan(tmp_path, "pooled", *costing.apply_costs(HALL_DOMAIN, HALL_PROBLEM, table.means()))
    pooled_actions = [" ".join(a) for a in pooled.actions]
    # Pooled: P1 = P2 = 90 + 90 + 160 = 340 against P3 = 170 + 160 = 330, so P3 (truly 320).
    assert pooled_actions == HALL_ROUTES["P3"]

    model = keyed_model(HALL_DOMAIN, HALL_PROBLEM, positions)
    keyed = _plan(tmp_path, "keyed", *apply_keyed_costs(model, table.keyed_cost))
    keyed_actions = [" ".join(a) for a in model.strip(keyed).actions]
    assert keyed_actions == HALL_ROUTES["P1"]
    assert keyed.cost == 270  # the surrogate equals the truth when every pair is measured
    assert true_ticks(keyed_actions, positions) < true_ticks(pooled_actions, positions)
