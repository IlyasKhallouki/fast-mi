"""Where each ground action leaves ego, and the position context of each plan action (Phase 8).

Action durations are near-deterministic once you know where ego stands when
the action starts: the walk to the next exit is long or short depending on the
spot the previous action left him on. A **position token** names that spot:

- ``start``: where the segment starts (the problem's initial ``(at R)``);
- ``entry:<from>:<to>:<id>``: ego arrived in PDDL room ``<to>`` through exit
  object ``<id>`` of ``<from>`` (``actor<n>`` for an actor);
  ``entry:<from>:<to>`` when no sentence names the exit;
- ``obj:<room>:<id>``: ego walked to object ``<id>`` in PDDL room ``<room>``
  (``actor:<room>:<n>`` for an actor).

**Anchors** (the token an action leaves), derived from the PDDL action's
effects on ``(at ?r)`` and the action's ``steps.toml`` template:

1. An action that changes ``(at ...)`` (every ``walk*``, including scripted
   room changes such as the Fester cutscene) leaves ego at
   ``entry:<from>:<to>:<id>``. ``<id>`` is the exit object: the object its
   last sentence step walks to, chosen as in rule 2. A room change with no
   sentence on a room object (the circus helmet's click-only step) leaves
   ``entry:<from>:<to>``. The exit object is part of the token because two
   exits between the same rooms can land ego on different spots: dock 905
   puts him at x 566, 904 at x 308 (``room-083-cu-dock/obj-0905-dock.txt
   [0019]``, ``obj-0904-dock.txt [0019]``). Two actions on the same exit
   share the token (the split bar exits, the gate variants at 215). Twins
   on different objects get different tokens even where they land on the
   same spot (path 686 runs 685's code): the template does not say where
   the destination room puts ego, so the split costs only samples, never
   accuracy.
2. Otherwise the **last sentence step** decides (``verb`` + ``obj`` [+
   ``obj2``]). Ego walks to a *room* object, never to an inventory object.
   The anchor is ``obj2`` if it lies in the room, else ``obj`` if it does,
   else nothing (an inventory-only sentence). Preferring ``obj2`` matches the
   sentence script on every two-object sentence of the route: global script 2
   walks to ``obj`` only while ``obj`` is a room object (``[027A]``-``[02A1]``),
   and the class-7 auto pick-up of a room ``obj`` chains on to ``obj2``
   (``[0229]``-``[0251]``, e.g. Use meat with pot ends at the pot).
3. Dialogue-only and click-only actions (no sentence step) leave the position
   unchanged, and so do inventory-only sentences.

**Room objects.** ``steps.toml`` references an inventory object in the room
it *starts* in, so an object lies in the action's room when its reference
room equals that PDDL room's *object room*: the step's ``room``, or for steps
without one (forest pseudo-rooms, which share room 58's objects) the room
learned from the room's exits (the objects its ``walk_to`` exits name). This is
a heuristic about references, not engine state: an item picked up in the very
room it is later used in from the inventory still looks like a room object,
which only matters in a one-object sentence (a two-object one prefers
``obj2``).

**Ambiguity fails loudly** (``PositionError``): a room change without exactly
one ``(at from)`` precondition and one ``(at to)`` add, two rooms in a
precondition, an action without a template (a room change needs one to name
its exit), a room-agnostic
action (no ``(at ...)`` precondition) with a step that names a room, a
room-less step in a room whose object room is unknown or conflicting, an
unresolvable object.

**Contexts.** The context of a plan action is the token just before it: start
at ``start``; after each action, its anchor (if it has one) becomes the
position. ``Positions.contexts`` derives them from the plan alone, in Python,
never from the engine, and checks that each action runs in the room ego is in.
"""

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from speedrun.compiler import CompileError, ObjectIndex, load_steps
from speedrun.costing import (
    ANY as ANY,  # re-exported: the shared context of unkeyed rooms
    CostingError,
    _Action,
    _actions,
    _atom_args,
    _effect_predicates,
    _ground_instances,
    _init,
    _init_facts,
    _List,
    _parse,
)

START = "start"
# ANY (from speedrun.costing): the single context of every room that is not keyed (speedrun.keyed).
AT = "at"
_PDDL_NAME = re.compile(r"^[a-z][a-z0-9_-]*$")


class PositionError(Exception):
    """An anchor cannot be derived unambiguously, or a plan contradicts the positions."""


@dataclass(frozen=True)
class Anchor:
    """Where a ground action runs and where it leaves ego."""

    room: str | None  # the PDDL room it needs ego in; None: any room (inventory-only)
    to: str | None  # the room it moves ego to (room changes only)
    token: str | None  # the position after it; None: unchanged


def pddl_name(token: str) -> str:
    """The PDDL object name of a position token: ``entry:a:b:905`` -> ``p_entry_a_b_905``.

    PDDL room names contain hyphens but no underscores, so ``_`` is unambiguous,
    and the ``p_`` prefix keeps tokens apart from the domain's own constants.
    """
    name = "p_" + token.replace(":", "_").lower()
    if not _PDDL_NAME.match(name):
        raise PositionError(f"position token {token!r} does not make a PDDL name ({name!r})")
    return name


class Positions:
    """Anchors of every ground action, and the room of every position token."""

    def __init__(self, initial_room: str, anchors: dict[str, Anchor]):
        self.initial_room = initial_room
        self._anchors = dict(anchors)
        self._rooms: dict[str, str] = {START: initial_room}
        for action, anchor in self._anchors.items():
            if anchor.token is not None:
                room = anchor.to or anchor.room
                if room is None:
                    raise PositionError(f"{action}: anchor {anchor.token!r} has no room")
                if self._rooms.setdefault(anchor.token, room) != room:
                    raise PositionError(f"token {anchor.token!r} lies in both {self._rooms[anchor.token]} and {room}")
        names: dict[str, str] = {}
        for token in self._rooms:
            other = names.setdefault(pddl_name(token), token)
            if other != token:
                raise PositionError(f"tokens {other!r} and {token!r} have the same PDDL name")

    def actions(self) -> list[str]:
        return sorted(self._anchors)

    def anchor(self, action: str) -> Anchor:
        try:
            return self._anchors[action]
        except KeyError:
            raise PositionError(f"{action!r} is not a ground action of the model") from None

    def tokens(self) -> list[str]:
        return sorted(self._rooms)

    def room_of(self, token: str) -> str:
        try:
            return self._rooms[token]
        except KeyError:
            raise PositionError(f"unknown position token {token!r}") from None

    def tokens_in(self, room: str) -> list[str]:
        return sorted(t for t, r in self._rooms.items() if r == room)

    def rooms(self) -> list[str]:
        """Every PDDL room an action runs in, enters, or the segment starts in."""
        rooms = {self.initial_room}
        for anchor in self._anchors.values():
            rooms |= {r for r in (anchor.room, anchor.to) if r is not None}
        return sorted(rooms)

    def contexts(self, actions: Sequence[str]) -> list[str]:
        """The position token just before each plan action."""
        pos = START
        out = []
        for i, action in enumerate(actions):
            anchor = self.anchor(action)
            room = self._rooms[pos]
            if anchor.room is not None and anchor.room != room:
                raise PositionError(
                    f"plan action {i} {action!r} runs in {anchor.room}, but ego is in {room} (position {pos})"
                )
            out.append(pos)
            if anchor.token is not None:
                pos = anchor.token
        return out


# --- derivation ---------------------------------------------------------------------


def _at_literals(expr: _List | None, what: str) -> tuple[list[list[str]], list[list[str]]]:
    """``(at x)`` literals of a precondition or effect: (positive, negative) argument lists."""
    pos: list[list[str]] = []
    neg: list[list[str]] = []
    if expr is None:
        return pos, neg

    def visit(e: _List, negated: bool) -> None:
        head = e.head
        if head == "and":
            for sub in e.lists():
                visit(sub, negated)
        elif head == "not":
            for sub in e.lists():
                visit(sub, not negated)
        elif head == AT:
            args = _atom_args(e)
            if args is None or len(args) != 1:
                raise PositionError(f"{what}: malformed (at ...) literal")
            (neg if negated else pos).append(args)
        elif head in ("or", "imply", "exists", "forall", "when") and _mentions_at(e):
            raise PositionError(f"{what}: (at ...) inside ({head} ...) is not supported")

    visit(expr, False)
    return pos, neg


def _mentions_at(e: _List) -> bool:
    return e.head == AT or any(_mentions_at(sub) for sub in e.lists())


@dataclass
class _Ground:
    name: str  # the ground action string, the steps.toml key
    room: str | None
    to: str | None


def _ground_rooms(domain_text: str, problem_text: str) -> tuple[str, list[_Ground]]:
    try:
        domain = _parse(domain_text, "domain")
        problem = _parse(problem_text, "problem")
        actions = _actions(domain)
        init = _init(problem)
    except CostingError as e:
        raise PositionError(str(e)) from e
    facts = _init_facts(init)
    initial = [args[0] for args in facts.get(AT, []) if len(args) == 1]
    if len(initial) != 1:
        raise PositionError(f"problem: expected exactly one (at <room>) in :init, found {initial}")
    fluents = set().union(*(_effect_predicates(a.effect) for a in actions)) if actions else set()
    out = []
    for action in actions:
        out += _ground_action_rooms(action, fluents, facts)
    return initial[0], out


def _ground_action_rooms(action: _Action, fluents: set[str], facts) -> list[_Ground]:
    pre_pos, _ = _at_literals(action.precondition, f"action {action.name}")
    add, delete = _at_literals(action.effect, f"action {action.name}")
    if action.params:
        try:
            instances = _ground_instances(action, fluents, facts)
        except CostingError as e:
            raise PositionError(str(e)) from e
    else:
        instances = [()]
    variables = [v for v, _ in action.params]
    out = []
    for args in instances:
        bind = dict(zip(variables, args))
        ground = " ".join((action.name, *args))

        def rooms(literals: list[list[str]]) -> list[str]:
            return sorted({bind.get(a[0], a[0]) for a in literals})  # noqa: B023

        pre, adds, dels = rooms(pre_pos), rooms(add), rooms(delete)
        if len(pre) > 1:
            raise PositionError(f"{ground}: its precondition puts ego in several rooms {pre}")
        room = pre[0] if pre else None
        to = None
        if adds or dels:
            if room is None:
                raise PositionError(f"{ground}: changes (at ...) but has no (at <from>) precondition")
            if len(adds) != 1 or dels != [room] or adds == [room]:
                raise PositionError(
                    f"{ground}: a room change must delete (at {room}) and add one other room, "
                    f"got add {adds}, delete {dels}"
                )
            to = adds[0]
        out.append(_Ground(ground, room, to))
    return out


def _templates(steps: Mapping, ground: str) -> list[dict]:
    entry = (steps.get("actions") or {}).get(ground)
    templates = entry.get("steps") if isinstance(entry, Mapping) else None
    if not isinstance(templates, list) or not templates or not all(isinstance(t, Mapping) for t in templates):
        raise PositionError(f"{ground}: no step template in steps.toml, so its anchor is unknown")
    return templates


def _is_walk_to(steps: Mapping, keyword: object) -> bool:
    name = (steps.get("verbs") or {}).get(keyword) if isinstance(keyword, str) else None
    return isinstance(name, str) and name.strip().casefold() == "walk to"


def _object_rooms(grounds: list[_Ground], steps: Mapping) -> dict[str, set[int]]:
    """PDDL room -> the room number its objects are referenced in (one, unless the model is inconsistent)."""
    found: dict[str, set[int]] = {}
    for g in grounds:
        if g.room is None:
            continue
        entry = (steps.get("actions") or {}).get(g.name)
        templates = entry.get("steps") if isinstance(entry, Mapping) else None
        if not isinstance(templates, list) or not templates:
            continue
        # A room change's later steps may run in the new room: only its first step counts.
        for step in templates[:1] if g.to is not None else templates:
            if not isinstance(step, Mapping):
                continue
            if isinstance(step.get("room"), int):
                found.setdefault(g.room, set()).add(step["room"])
            obj = step.get("obj")
            if g.to is not None and _is_walk_to(steps, step.get("verb")) and isinstance(obj, Mapping):
                if isinstance(obj.get("room"), int):
                    found.setdefault(g.room, set()).add(obj["room"])  # an exit lies in the room it leaves
    return found


def _sentence_token(g: _Ground, steps: Mapping, objects: ObjectIndex, object_rooms: dict[str, set[int]]) -> str | None:
    templates = _templates(steps, g.name)
    if g.room is None:
        roomed = [t for t in templates if "room" in t]
        if roomed:
            raise PositionError(
                f"{g.name}: no (at ...) precondition (any room), but its step runs in room {roomed[0]['room']}"
            )
        return None  # inventory only: ego does not move
    sentences = [t for t in templates if "verb" in t]
    if not sentences:
        return None  # dialogue-only or click-only
    step = sentences[-1]
    rooms = object_rooms.get(g.room, set())
    if len(rooms) != 1:
        what = "unknown" if not rooms else f"ambiguous ({sorted(rooms)})"
        raise PositionError(f"{g.name}: the object room of {g.room} is {what}, so its anchor cannot be derived")
    (object_room,) = rooms
    for key in ("obj2", "obj"):
        ref = step.get(key)
        if not isinstance(ref, Mapping):
            continue
        if "actor" in ref:
            return f"actor:{g.room}:{ref['actor']}"
        if ref.get("room") != object_room:
            continue  # an inventory object
        try:
            oid = objects.resolve_object(ref)
        except CompileError as e:
            raise PositionError(f"{g.name}: {e}") from e
        return f"obj:{g.room}:{oid}"
    return None


def _entry_token(g: _Ground, steps: Mapping, objects: ObjectIndex, object_rooms: dict[str, set[int]]) -> str:
    """``entry:<from>:<to>:<exit>`` for a room change; ``entry:<from>:<to>`` if no sentence names its exit."""
    base = f"entry:{g.room}:{g.to}"
    spot = _sentence_token(g, steps, objects, object_rooms)  # the room object the exit sentence walks to
    if spot is None:
        return base
    kind, _, ident = spot.split(":")
    return f"{base}:{ident}" if kind == "obj" else f"{base}:actor{ident}"


def derive_positions(domain_text: str, problem_text: str, steps: Mapping, objects: ObjectIndex) -> Positions:
    """Every ground action's anchor; see the module doc. Raises ``PositionError`` on any ambiguity."""
    initial, grounds = _ground_rooms(domain_text, problem_text)
    object_rooms = _object_rooms(grounds, steps)
    conflicts = {r: rooms for r, rooms in object_rooms.items() if len(rooms) > 1}
    if conflicts:
        room, rooms = sorted(conflicts.items())[0]
        raise PositionError(f"room {room}: its steps reference objects in several rooms {sorted(rooms)}")
    anchors: dict[str, Anchor] = {}
    for g in grounds:
        if g.to is not None:
            anchors[g.name] = Anchor(g.room, g.to, _entry_token(g, steps, objects, object_rooms))
        else:
            anchors[g.name] = Anchor(g.room, None, _sentence_token(g, steps, objects, object_rooms))
    return Positions(initial, anchors)


def load_positions(domain: Path, problem: Path, steps: Path, objects_path: Path) -> Positions:
    """``derive_positions`` from files. Unreadable inputs are a ``PositionError`` too."""
    try:
        templates = load_steps(steps)
        objects = ObjectIndex.from_dump(objects_path)
        domain_text = Path(domain).read_text(encoding="utf-8")
        problem_text = Path(problem).read_text(encoding="utf-8")
    except (OSError, ValueError, CompileError) as e:
        raise PositionError(f"cannot derive positions: {e}") from e
    return derive_positions(domain_text, problem_text, templates, objects)
