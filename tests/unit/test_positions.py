"""Unit tests for ``speedrun.positions``: where each action leaves ego, and the context of each plan action.

A position token names where ego stands: ``start`` (the segment start),
``entry:<from>:<to>`` (he arrived in ``<to>`` through the exit from
``<from>``) or ``obj:<room>:<id>`` (he walked to object ``<id>`` in PDDL room
``<room>``). The toy ``town`` model below exercises every derivation rule; the
last tests run the derivation on the real Part I model.
"""

import json
import re

import pytest

from speedrun import paths
from speedrun.compiler import ObjectIndex
from speedrun.positions import ANY, START, PositionError, derive_positions, pddl_name

TOWN_DOMAIN = """\
;; Toy town for the position tests (src: synthetic).
(define (domain town)
  (:requirements :strips :typing :negative-preconditions :action-costs)
  (:types room)
  (:constants street shop yard attic - room)
  (:predicates (at ?r - room) (link ?from ?to - room) (door-open) (has-key) (has-coin) (polished)
               (answered) (waved) (has-flower) (dusted))
  (:functions (total-cost) - number)
  (:action walk
    :parameters (?from ?to - room)
    :precondition (and (at ?from) (link ?from ?to))
    :effect (and (not (at ?from)) (at ?to) (increase (total-cost) 1)))
  (:action open-door
    :parameters ()
    :precondition (and (at street) (not (door-open)))
    :effect (and (door-open) (increase (total-cost) 1)))
  (:action walk-into-shop
    :parameters ()
    :precondition (and (at street) (door-open))
    :effect (and (not (at street)) (at shop) (increase (total-cost) 1)))
  (:action buy-key
    :parameters ()
    :precondition (and (at shop) (not (has-key)))
    :effect (and (has-key) (increase (total-cost) 1)))
  (:action give-coin
    :parameters ()
    :precondition (and (at shop) (has-coin))
    :effect (and (not (has-coin)) (increase (total-cost) 1)))
  (:action use-key-with-lock
    :parameters ()
    :precondition (and (at shop) (has-key))
    :effect (and (answered) (increase (total-cost) 1)))
  (:action polish-coin
    :parameters ()
    :precondition (and (has-coin) (not (polished)) (not (at yard)))
    :effect (and (polished) (increase (total-cost) 1)))
  (:action answer-clerk
    :parameters ()
    :precondition (and (at shop))
    :effect (and (answered) (increase (total-cost) 1)))
  (:action wave
    :parameters ()
    :precondition (and (at shop))
    :effect (and (waved) (increase (total-cost) 1)))
  (:action pick-flower
    :parameters ()
    :precondition (and (at yard))
    :effect (and (has-flower) (increase (total-cost) 1)))
)
"""

TOWN_PROBLEM = """\
(define (problem town-1)
  (:domain town)
  (:init
    (at street)
    (has-coin)
    (link street yard) ; src: synthetic gate
    (link yard street)
    (link shop street)
    (= (total-cost) 0))
  (:goal (and (has-flower) (answered)))
  (:metric minimize (total-cost)))
"""

TOWN_OBJECTS = {
    "verbs": [{"id": 11, "name": "Walk to"}, {"id": 2, "name": "Open"}, {"id": 13, "name": "Talk to"},
              {"id": 3, "name": "Give"}, {"id": 7, "name": "Use"}, {"id": 9, "name": "Pick up"}],
    "rooms": [
        {"room": 101, "objects": [{"id": 501, "name": "door"}, {"id": 503, "name": "coin"},
                                  {"id": 504, "name": "gate"}]},
        {"room": 102, "objects": [{"id": 511, "name": "clerk"}, {"id": 512, "name": "lock"},
                                  {"id": 513, "name": "key"}, {"id": 515, "name": "door"}]},
        {"room": 58, "objects": [{"id": 685, "name": "path"}, {"id": 678, "name": "flower"}]},
        {"room": 103, "objects": [{"id": 520, "name": "dust"}]},
    ],
}  # fmt: skip


def _step(verb, obj, room=None, obj2=None, **extra) -> dict:
    step = {"verb": verb, "obj": obj, **extra}
    if obj2 is not None:
        step["obj2"] = obj2
    if room is not None:
        step["room"] = room
    return step


def _ref(room, name, **extra) -> dict:
    return {"room": room, "name": name, **extra}


def town_steps() -> dict:
    return {
        "verbs": {"walk_to": "Walk to", "open": "Open", "talk_to": "Talk to", "give": "Give", "use": "Use",
                  "pick_up": "Pick up"},
        "actions": {
            "walk street yard": {"steps": [_step("walk_to", _ref(101, "gate"), room=101)]},
            # A forest-style step: no `room`, the pseudo-room is waited on in var 4.
            "walk yard street": {"steps": [_step("walk_to", _ref(58, "path"), until=[{"var": 4, "eq": 205}])]},
            "walk shop street": {"steps": [_step("walk_to", _ref(102, "door"), room=102)]},
            "open-door": {"steps": [_step("open", _ref(101, "door"), room=101)]},
            "walk-into-shop": {"steps": [_step("walk_to", _ref(101, "door"), room=101)]},
            # The last *sentence* step names the anchor; a dialogue-only step after it moves nothing.
            "buy-key": {"steps": [_step("talk_to", _ref(102, "clerk"), room=102, choose=["key"]),
                                  {"choose": ["thanks"]}]},
            # The coin is an inventory object (referenced where it starts): ego walks to the clerk.
            "give-coin": {"steps": [_step("give", _ref(101, "coin"), obj2=_ref(102, "clerk"), room=102)]},
            # Both objects look like room objects (the key started in the shop): obj2 wins.
            "use-key-with-lock": {"steps": [_step("use", _ref(102, "key"), obj2=_ref(102, "lock"), room=102)]},
            # Inventory only, in any room: ego does not move.
            "polish-coin": {"steps": [_step("use", _ref(101, "coin"), obj2=_ref(102, "key"))]},
            "answer-clerk": {"steps": [{"choose": ["goodbye"]}]},
            "wave": {"steps": [{"room": 102, "click": [{"verb": "use"}]}]},
            "pick-flower": {"steps": [_step("pick_up", _ref(58, "flower"), until=[{"var": 4, "eq": 205}])]},
        },
    }  # fmt: skip


@pytest.fixture
def objects() -> ObjectIndex:
    return ObjectIndex.from_dict(TOWN_OBJECTS)


def _derive(objects, domain=TOWN_DOMAIN, problem=TOWN_PROBLEM, steps=None):
    return derive_positions(domain, problem, town_steps() if steps is None else steps, objects)


# --- anchors -----------------------------------------------------------------------


def test_walks_leave_ego_at_the_entry_of_the_destination(objects):
    pos = _derive(objects)
    for a, b in (("street", "yard"), ("yard", "street"), ("shop", "street")):
        anchor = pos.anchor(f"walk {a} {b}")
        assert (anchor.room, anchor.to, anchor.token) == (a, b, f"entry:{a}:{b}")


def test_a_guarded_room_change_is_an_entry_too(objects):
    anchor = _derive(objects).anchor("walk-into-shop")
    assert (anchor.room, anchor.to, anchor.token) == ("street", "shop", "entry:street:shop")


def test_a_sentence_leaves_ego_at_its_object(objects):
    pos = _derive(objects)
    assert pos.anchor("open-door").token == "obj:street:501"
    assert pos.anchor("open-door").room == "street" and pos.anchor("open-door").to is None
    # The last sentence step counts; the dialogue-only step after it does not move ego.
    assert pos.anchor("buy-key").token == "obj:shop:511"


def test_an_inventory_object_is_not_walked_to(objects):
    # give coin (inventory, referenced in room 101) to clerk (room 102, the step's room)
    assert _derive(objects).anchor("give-coin").token == "obj:shop:511"


def test_with_two_room_objects_the_second_one_is_the_anchor(objects):
    assert _derive(objects).anchor("use-key-with-lock").token == "obj:shop:512"


def test_inventory_only_dialogue_only_and_click_only_actions_leave_the_position(objects):
    pos = _derive(objects)
    polish = pos.anchor("polish-coin")
    assert (polish.room, polish.token) == (None, None)  # no (at ...) precondition: any room
    for action in ("answer-clerk", "wave"):
        assert (pos.anchor(action).room, pos.anchor(action).token) == ("shop", None)


def test_a_step_without_room_uses_the_object_room_of_its_pddl_room(objects):
    # yard is a forest-style pseudo-room: its exit (walk yard street) references objects
    # in room 58, so the flower (room 58) lies in the yard.
    assert _derive(objects).anchor("pick-flower").token == "obj:yard:678"


def test_tokens_know_their_room(objects):
    pos = _derive(objects)
    assert pos.initial_room == "street"
    assert pos.room_of(START) == "street"
    assert pos.room_of("entry:street:shop") == "shop"
    assert pos.room_of("obj:yard:678") == "yard"
    assert set(pos.tokens_in("street")) == {START, "obj:street:501", "entry:yard:street", "entry:shop:street"}
    assert set(pos.tokens_in("shop")) == {"entry:street:shop", "obj:shop:511", "obj:shop:512"}
    assert pos.tokens_in("attic") == []


# --- anchors: ambiguity fails loudly --------------------------------------------------


def _add_action(domain: str, text: str) -> str:
    return domain.rstrip().removesuffix(")") + text + ")\n"


def test_a_room_change_without_a_from_room_fails(objects):
    domain = _add_action(TOWN_DOMAIN, """
  (:action teleport
    :parameters ()
    :precondition (and (door-open))
    :effect (and (at yard) (increase (total-cost) 1)))
""")
    with pytest.raises(PositionError, match="teleport"):
        _derive(objects, domain=domain)


def test_two_rooms_in_a_precondition_fail(objects):
    domain = _add_action(TOWN_DOMAIN, """
  (:action stretch
    :parameters ()
    :precondition (and (at street) (at shop))
    :effect (and (waved) (increase (total-cost) 1)))
""")
    steps = town_steps()
    steps["actions"]["stretch"] = {"steps": [{"choose": ["x"]}]}
    with pytest.raises(PositionError, match="stretch"):
        _derive(objects, domain=domain, steps=steps)


def test_an_action_without_a_template_fails(objects):
    steps = town_steps()
    del steps["actions"]["open-door"]
    with pytest.raises(PositionError, match="open-door"):
        _derive(objects, steps=steps)


def test_a_room_agnostic_action_with_a_room_step_fails(objects):
    steps = town_steps()
    steps["actions"]["polish-coin"]["steps"][0]["room"] = 101
    with pytest.raises(PositionError, match="polish-coin"):
        _derive(objects, steps=steps)


def test_a_roomless_step_in_a_room_with_unknown_objects_fails(objects):
    domain = _add_action(TOWN_DOMAIN, """
  (:action dust
    :parameters ()
    :precondition (and (at attic))
    :effect (and (dusted) (increase (total-cost) 1)))
""")
    steps = town_steps()
    steps["actions"]["dust"] = {"steps": [_step("pick_up", _ref(103, "dust"))]}
    with pytest.raises(PositionError, match="dust"):
        _derive(objects, domain=domain, steps=steps)


def test_conflicting_object_rooms_fail(objects):
    steps = town_steps()
    steps["actions"]["pick-flower"]["steps"][0]["room"] = 101  # the yard's exit says room 58
    with pytest.raises(PositionError, match="yard"):
        _derive(objects, steps=steps)


def test_an_unresolvable_object_fails(objects):
    steps = town_steps()
    steps["actions"]["open-door"]["steps"][0]["obj"] = _ref(101, "window")
    with pytest.raises(PositionError, match="open-door"):
        _derive(objects, steps=steps)


# --- contexts ------------------------------------------------------------------------


PLAN = ["open-door", "walk-into-shop", "buy-key", "answer-clerk", "give-coin", "polish-coin",
        "use-key-with-lock", "walk shop street", "walk street yard", "pick-flower", "walk yard street"]  # fmt: skip


def test_the_context_is_the_position_before_each_action(objects):
    contexts = _derive(objects).contexts(PLAN)
    assert contexts == [
        START,                 # open-door: the segment start
        "obj:street:501",      # walk-into-shop: at the door just opened
        "entry:street:shop",   # buy-key: just came in
        "obj:shop:511",        # answer-clerk: at the clerk
        "obj:shop:511",        # give-coin: dialogue-only moved nothing
        "obj:shop:511",        # polish-coin: still at the clerk
        "obj:shop:511",        # use-key-with-lock: polishing moved nothing
        "obj:shop:512",        # walk shop street: at the lock
        "entry:shop:street",   # walk street yard
        "entry:street:yard",   # pick-flower
        "obj:yard:678",        # walk yard street
    ]  # fmt: skip


def test_an_action_in_the_wrong_room_fails(objects):
    with pytest.raises(PositionError, match="buy-key"):
        _derive(objects).contexts(["buy-key"])  # ego starts on the street


def test_an_unknown_action_fails(objects):
    with pytest.raises(PositionError, match="fly-away"):
        _derive(objects).contexts(["open-door", "fly-away"])


def test_pddl_names():
    # Prefixed, so a token never collides with a room constant (a toy room may be called "start").
    assert pddl_name(START) == "p_start"
    assert pddl_name(ANY) == "p_any"
    assert pddl_name("entry:high-street-town:jail") == "p_entry_high-street-town_jail"
    assert pddl_name("obj:kitchen:567") == "p_obj_kitchen_567"
    for token in ("entry:a:b", "obj:f215:678"):
        assert re.fullmatch(r"[a-z][a-z0-9_-]*", pddl_name(token))


# --- the real Part I model ------------------------------------------------------------

REAL_OBJECTS = paths.ROOT / "out" / "objects.json"
SEG = paths.ROOT / "pddl" / "part1"


@pytest.fixture(scope="module")
def real():
    if not REAL_OBJECTS.is_file():
        pytest.skip("OBJECT DUMP MISSING: out/objects.json not found — run `speedrun dump-objects`; "
                    "the real model's anchors were NOT checked")  # fmt: skip
    import tomllib

    steps = tomllib.loads((SEG / "steps.toml").read_text(encoding="utf-8"))
    return derive_positions((SEG / "domain.pddl").read_text(), (SEG / "problem.pddl").read_text(), steps,
                            ObjectIndex.from_dump(REAL_OBJECTS))  # fmt: skip


def test_real_model_every_steps_action_has_an_anchor(real):
    import tomllib

    steps = tomllib.loads((SEG / "steps.toml").read_text(encoding="utf-8"))
    assert set(real.actions()) == set(steps["actions"])


@pytest.mark.parametrize(("action", "room", "token"), [
    ("walk dock lookout", "dock", "entry:dock:lookout"),
    ("walk-out-of-bar-from-left-meanwhile", "bar-left", "entry:bar-left:dock"),
    ("walk-out-of-tent-after-helmet-meat", "tent", "entry:tent:clearing"),  # click-only, but a room change
    ("walk-past-fester-to-underwater", "foyer", "entry:foyer:underwater"),  # a cutscene moves him
    ("open-store-door", "high-street-town", "obj:high-street-town:437"),
    ("open-mansion-door", "mansion", "obj:mansion:465"),
    ("use-meat-with-pot", "kitchen", "obj:kitchen:567"),
    ("put-meat-in-stew", "kitchen", "obj:kitchen:574"),  # the meat is held: ego walks to the stew
    ("use-meat-on-table-with-petal", "kitchen", "obj:kitchen:566"),  # the petal is held
    ("give-meat-to-poodles", "mansion", "obj:mansion:467"),
    ("dig-treasure", "treasure-site", "obj:treasure-site:749"),
    ("pick-up-petal", "f215", "obj:f215:678"),
    # Alternative exits (model.md section 14.8): 686 runs 685's code, which loads 215 or 210
    # with ego at 687, so the arrival is the twin's. 905 lands at x 566, not 904's 308, but a
    # room change's token names only from and to: both docks give entry:cu-dock:dock.
    ("walk-f218-f215-via-686", "f218", "entry:f218:f215"),
    ("walk-f220-f210-via-686", "f220", "entry:f220:f210"),
    ("walk-cu-dock-dock-via-905", "cu-dock", "entry:cu-dock:dock"),
    ("drug-meat-with-petal", None, None),
    ("open-cake", None, None),
])  # fmt: skip
def test_real_model_anchors(real, action, room, token):
    anchor = real.anchor(action)
    assert (anchor.room, anchor.token) == (room, token)


def test_real_model_contexts_of_the_reported_plan(real):
    report = paths.ROOT / "out" / "optimize" / "20261005T073926Z" / "report.json"
    if not report.is_file():
        pytest.skip("OPTIMIZE REPORT MISSING: out/optimize/20261005T073926Z/report.json")
    actions = json.loads(report.read_text())["winner"]["actions"]
    contexts = real.contexts(actions)
    by_index = list(zip(actions, contexts))
    assert by_index[0] == ("open-bar-door", START)
    assert ("walk dock lookout", "entry:bar-left:dock") in by_index  # after the first bar exit
    assert ("walk dock lookout", "entry:cu-dock:dock") in by_index
    assert ("walk-into-foyer", "obj:mansion:465") in by_index  # right after opening the door
    assert ("walk-into-foyer", "entry:high-street-mansion:mansion") in by_index
    assert ("walk high-street-town jail", "entry:low-street:high-street-town") in by_index
    assert ("walk high-street-town jail", "entry:high-street-mansion:high-street-town") in by_index
    # open-cake (inventory only) does not move ego: the walk after it starts at the jail's exit.
    k = actions.index("open-cake")
    assert contexts[k] == contexts[k + 1] == "entry:jail:high-street-town"
