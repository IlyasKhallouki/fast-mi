"""A synthetic toy world for the Phase 7 extraction tests (citations, merge, diff, CLI).

Nothing here is real game data: rooms 90 (yard), 91 (hall), 92 (cellar) and
93 (attic), objects 901-910, and a script dump with a handful of offsets.

The toy route: pick up the coin (Var[195] money), open the door, walk into
the hall, take the chest (Bit[85]), give the coin to the statue (Bit[86]).
"""

from pathlib import Path

# --- a synthetic descumm dump (data/scripts layout) -----------------------------

SCRIPT_FILES = {
    "global/script-002.txt": "[02DB] (11) walkActorToObject(VAR_EGO,VAR_ACTIVE_OBJECT1);\n",
    "global/script-071.txt": "[008D] (1A) Bit[83 + Local[0]] = 1;\n",
    "room-090-yard/obj-0901-door.txt": (
        "# object 901 \"door\" in room 90\n"
        "[0010] (0A) startScript(25,[901,0]);\n"
        "[0018] (00) stopObjectCode();\n"
        "[0020] (0F) VAR_RESULT = getObjectState(901);\n"
        "[0028] (24) loadRoomWithEgo(903,91,-1,-1);\n"
    ),
    "room-090-yard/obj-0904-coin.txt": "[0010] (2E) pickupObject(904,90);\n[0016] (5A) Var[195] += 100;\n",
    "room-091-hall/obj-0902-chest.txt": "[0010] (2E) pickupObject(902,91);\n[0015] (1A) Bit[85] = 1;\n",
    "room-091-hall/obj-0903-gate.txt": "[000C] (24) loadRoomWithEgo(901,90,-1,-1);\n",
    "room-091-hall/obj-0905-statue.txt": "[0012] (1A) Bit[86] = 1;\n",
    "room-091-hall/obj-0906-bell.txt": "[0010] (1C) startSound(12);\n",
    "room-091-hall/obj-0907-trapdoor.txt": "[000C] (24) loadRoomWithEgo(911,92,-1,-1);\n",
    "room-091-hall/obj-0908-ladder.txt": "[000C] (24) loadRoomWithEgo(909,93,-1,-1);\n",
    "room-093-attic/obj-0909-hatch.txt": "[000C] (24) loadRoomWithEgo(908,91,-1,-1);\n",
    "room-093-attic/obj-0910-window.txt": "[000C] (24) loadRoomWithEgo(0,94,-1,-1);\n",
}


def make_scripts(root: Path) -> Path:
    """Write the synthetic script dump under ``root`` and return it."""
    for rel, text in SCRIPT_FILES.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    return root


# --- extraction fragments --------------------------------------------------------

DOOR_SRC = "; src: data/scripts/room-090-yard/obj-0901-door.txt [0010] — Open 901 runs script 25: state 1"


def action(
    name: str,
    *,
    src: tuple[str, ...] = (DOOR_SRC,),
    inputs: tuple[str, ...] = ("; sentence: 2 901",),
    room: str | None = "; room: 90",
    extra: tuple[str, ...] = (),
    params: str | None = None,
    pre: str | None = "(and (at-r90) (state-o901-0))",
    eff: str = "(and (not (state-o901-0)) (state-o901-1) (increase (total-cost) 1))",
) -> str:
    """One annotated fragment action; every part can be replaced or dropped to break it."""
    lines = [*src, *inputs, *([room] if room else []), *extra, f"(:action {name}"]
    if params is not None:
        lines.append(f"  :parameters {params}")
    if pre is not None:
        lines.append(f"  :precondition {pre}")
    lines.append(f"  :effect {eff})")
    return "\n".join(lines) + "\n"


YARD = """\
;; Toy yard (room 90): the coin and the door.
; src: data/scripts/room-090-yard/obj-0904-coin.txt [0010] — Pick up 904 puts the coin in the inventory
; src: data/scripts/room-090-yard/obj-0904-coin.txt [0016] — and adds 100 to Var[195]
; sentence: 9 904
; room: 90
(:action pick-up-coin
  :parameters ()
  :precondition (and (at-r90) (owner-o904-15))
  :effect (and (not (owner-o904-15)) (has-o904) (var-195-ge-100) (increase (total-cost) 1)))

; src: data/scripts/room-090-yard/obj-0901-door.txt [0010] — Open 901 runs script 25: state 1
; sentence: 2 901
; room: 90
(:action open-door
  :parameters ()
  :precondition (and (at-r90) (state-o901-0))
  :effect (and (not (state-o901-0)) (state-o901-1) (increase (total-cost) 1)))

; src: data/scripts/room-090-yard/obj-0901-door.txt [0020] — Walk to 901 needs state 1
; src: data/scripts/room-090-yard/obj-0901-door.txt [0028] — then loadRoomWithEgo(903,91)
; sentence: 11 901
; room: 90
(:action walk-yard-to-hall
  :parameters ()
  :precondition (and (at-r90) (state-o901-1))
  :effect (and (not (at-r90)) (at-r91) (increase (total-cost) 1)))
"""

HALL = """\
;; Toy hall (room 91).
; src: data/scripts/room-091-hall/obj-0902-chest.txt [0010] — Pick up 902
; src: data/scripts/room-091-hall/obj-0902-chest.txt [0015] — sets Bit[85]
; sentence: 9 902
; room: 91
; dialogue: yes please
; dialogue: thanks
(:action take-chest
  :parameters ()
  :precondition (and (at-r91) (not (bit-85)) (var-54-eq--80))
  :effect (and (bit-85) (has-o902) (increase (total-cost) 1)))

; src: data/scripts/room-091-hall/obj-0905-statue.txt [0012] — Give 904 to 905 sets Bit[86]
; sentence: 4 904 905
; room: 91
(:action give-coin-to-statue
  :parameters ()
  :precondition (and (at-r91) (has-o904) (var-195-ge-100) (class-o905-6))
  :effect (and (not (has-o904)) (bit-86) (increase (total-cost) 1)))

; src: data/scripts/room-091-hall/obj-0903-gate.txt [000C] — Walk to 903 loads the yard
; sentence: 11 903
; room: 91
(:action walk-hall-to-yard
  :parameters ()
  :precondition (and (at-r91))
  :effect (and (not (at-r91)) (at-r90) (increase (total-cost) 1)))

; src: data/scripts/room-091-hall/obj-0907-trapdoor.txt [000C] — Walk to 907 loads the cellar
; sentence: 11 907
; room: 91
(:action walk-hall-to-cellar
  :parameters ()
  :precondition (and (at-r91))
  :effect (and (not (at-r91)) (at-r92) (increase (total-cost) 1)))

; src: data/scripts/room-091-hall/obj-0905-statue.txt [0012] — the statue reacts to the coin slot click
; click: 7,inv:904,-1
; room: 91
(:action wave-coin
  :parameters ()
  :precondition (and (at-r91) (has-o904))
  :effect (and (var-300-eq-1) (increase (total-cost) 1)))
"""

FRAGMENTS = {"yard.pddl": YARD, "hall.pddl": HALL}
YARD_ACTIONS = ["pick-up-coin", "open-door", "walk-yard-to-hall"]
HALL_ACTIONS = ["take-chest", "give-coin-to-statue", "walk-hall-to-yard", "walk-hall-to-cellar", "wave-coin"]

# --- a segment-start state dump (C7 shape: string keys for owners/states/classes) ---


def state_dump(**overrides) -> dict:
    vars_ = [0] * 800
    vars_[54] = -80
    state = {
        "tick": 812,
        "frame": 203,
        "room": 90,
        "ego": 1,
        "ego_pos": [160, 130],
        "seed": 1,
        "boot_param": 0,
        "vars": vars_,
        "bits_set": [116, 395],
        "inventory": [],
        "owners": {str(o): 15 for o in range(901, 911)} | {"1": 0},
        "states": {str(o): 0 for o in range(901, 911)} | {"1": 0},
        "classes": {"905": [6], "906": [32]},
        "room_objects": [],
        "verbs": [],
    }
    state.update(overrides)
    return state


GOAL = [{"bit": 85, "eq": 1}, {"bit": 86, "eq": 1}]

# --- a hand-written toy model (abstract predicates, named room nodes) --------------

HAND_DOMAIN = """\
(define (domain toy)
  (:requirements :strips :typing :negative-preconditions :action-costs)
  (:types room)
  (:constants yard hall attic roof - room)
  (:predicates (at ?r - room) (link ?from ?to - room) (door-open) (has-coin) (chest-taken) (bell-rung) (coin-rubbed))
  (:functions (total-cost) - number)

  ;; The generic walk.
  ; src: data/scripts/global/script-002.txt [02DB] — the sentence script walks ego to the exit
  (:action walk
    :parameters (?from ?to - room)
    :precondition (and (at ?from) (link ?from ?to))
    :effect (and (not (at ?from)) (at ?to) (increase (total-cost) 1)))

  ; src: data/scripts/room-090-yard/obj-0901-door.txt [0010] — Open 901
  ; src: data/scripts/room-090-yard/obj-0901-door.txt [0018] — stop
  (:action open-door
    :parameters ()
    :precondition (and (at yard) (not (door-open)))
    :effect (and (door-open) (increase (total-cost) 1)))

  ; src: data/scripts/room-090-yard/obj-0901-door.txt [0020] — Walk to 901 needs state 1
  (:action walk-through-door
    :parameters ()
    :precondition (and (at yard) (door-open))
    :effect (and (not (at yard)) (at hall) (increase (total-cost) 1)))

  ; src: data/scripts/room-090-yard/obj-0904-coin.txt [0010] — Pick up 904
  (:action pick-up-coin
    :parameters ()
    :precondition (and (at yard) (not (has-coin)))
    :effect (and (has-coin) (increase (total-cost) 1)))

  ; src: data/scripts/room-091-hall/obj-0902-chest.txt [0015] — Bit[85]
  (:action take-chest
    :parameters ()
    :precondition (and (at hall) (not (chest-taken)))
    :effect (and (chest-taken) (increase (total-cost) 1)))

  ; src: data/scripts/room-091-hall/obj-0906-bell.txt [0010] — Push 906
  (:action ring-bell
    :parameters ()
    :precondition (and (at hall))
    :effect (and (bell-rung) (increase (total-cost) 1)))

  ; src: data/scripts/room-090-yard/obj-0904-coin.txt [0016] — Use 904 anywhere
  (:action rub-coin
    :parameters ()
    :precondition (and (has-coin))
    :effect (and (coin-rubbed) (increase (total-cost) 1)))

  ; src: data/scripts/room-091-hall/obj-0902-chest.txt [0010] — a dialogue-only step
  (:action answer-parrot
    :parameters ()
    :precondition (and (at hall))
    :effect (and (increase (total-cost) 1))))
"""

HAND_PROBLEM = """\
(define (problem toy-trials)
  (:domain toy)
  (:init
    (at yard)
    (link hall yard) ; src: data/scripts/room-091-hall/obj-0903-gate.txt [000C] — gate loads the yard
    (link hall attic) ; src: data/scripts/room-091-hall/obj-0908-ladder.txt [000C] — ladder loads the attic
    (link attic hall) ; src: data/scripts/room-093-attic/obj-0909-hatch.txt [000C] — hatch loads the hall
    (link attic roof) ; src: data/scripts/room-093-attic/obj-0910-window.txt [000C] — window loads the roof
    (= (total-cost) 0))
  (:goal (and (chest-taken)))
  (:metric minimize (total-cost)))
"""

HAND_STEPS = """\
[verbs]
walk_to = "Walk to"
open = "Open"
pick_up = "Pick up"
push = "Push"
use = "Use"

[actions."walk hall yard"]
cite = "gate"
steps = [{verb = "walk_to", obj = {room = 91, name = "gate"}, room = 91}]

[actions."walk hall attic"]
cite = "ladder"
steps = [{verb = "walk_to", obj = {room = 91, name = "ladder"}, room = 91}]

[actions."walk attic hall"]
cite = "hatch"
steps = [{verb = "walk_to", obj = {room = 93, name = "hatch"}, room = 93}]

[actions."walk attic roof"]
cite = "window"
steps = [{verb = "walk_to", obj = {room = 93, name = "window"}, room = 93}]

[actions.open-door]
cite = "door"
steps = [{verb = "open", obj = {room = 90, name = "door"}, room = 90}]

[actions.walk-through-door]
cite = "door"
steps = [{verb = "walk_to", obj = {room = 90, name = "door"}, room = 90}]

[actions.pick-up-coin]
cite = "coin"
steps = [{verb = "pick_up", obj = {room = 90, name = "coin"}, room = 90}]

[actions.take-chest]
cite = "chest"
steps = [
  {verb = "walk_to", obj = {room = 91, name = "chest"}, room = 91},
  {verb = "pick_up", obj = {room = 91, name = "chest"}, room = 91, choose = ["yes please"]},
]

[actions.ring-bell]
cite = "bell"
steps = [{verb = "push", obj = {room = 91, name = "bell"}, room = 91}]

[actions.rub-coin]
cite = "coin"
steps = [{verb = "use", obj = {room = 90, name = "coin"}}]

[actions.answer-parrot]
cite = "parrot"
steps = [{choose = ["polly"]}]
"""

OBJECTS = {
    "rooms": [
        {"room": 90, "objects": [{"id": 901, "name": "door"}, {"id": 904, "name": "coin"}]},
        {
            "room": 91,
            "objects": [
                {"id": 902, "name": "chest"},
                {"id": 903, "name": "gate"},
                {"id": 905, "name": "statue"},
                {"id": 906, "name": "bell"},
                {"id": 907, "name": "trapdoor"},
                {"id": 908, "name": "ladder"},
            ],
        },
        {"room": 93, "objects": [{"id": 909, "name": "hatch"}, {"id": 910, "name": "window"}]},
    ],
    "verbs": [
        {"id": 2, "name": "Open"},
        {"id": 4, "name": "Give"},
        {"id": 5, "name": "Push"},
        {"id": 7, "name": "Use"},
        {"id": 9, "name": "Pick up"},
        {"id": 11, "name": "Walk to"},
    ],
}

SEGMENT_TOML = """\
name = "toy"
start = [{room = 90}]
goal = [{bit = 85, eq = 1}, {bit = 86, eq = 1}]
goal_cite = ["data/scripts/global/script-071.txt [008D] Bit[85]", "data/scripts/global/script-071.txt [008D] Bit[86]"]
"""


def make_hand_segment(pddl_dir: Path, name: str = "toy") -> Path:
    """Write the hand toy model as segment ``name`` under ``pddl_dir`` and return its directory."""
    seg = pddl_dir / name
    seg.mkdir(parents=True, exist_ok=True)
    (seg / "segment.toml").write_text(SEGMENT_TOML.replace('name = "toy"', f'name = "{name}"'), encoding="utf-8")
    (seg / "domain.pddl").write_text(HAND_DOMAIN, encoding="utf-8")
    (seg / "problem.pddl").write_text(HAND_PROBLEM, encoding="utf-8")
    (seg / "steps.toml").write_text(HAND_STEPS, encoding="utf-8")
    return seg
