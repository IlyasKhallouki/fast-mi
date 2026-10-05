"""Compile a Fast Downward plan into the plan player's JSONL (contract C4).

Each ground action, written as ``" ".join(action)`` (for example
``walk lookout island-map``), is looked up in the ``[actions]`` table of
``steps.toml`` (C8). Its step templates are expanded in order. Object names
are resolved to ids only through the engine's ``objects.json`` dump (C6).

A step template is a sentence (``verb`` + ``obj`` [+ ``obj2``]), a ``click``
list, or neither (a dialogue-only step, which needs ``choose``). Click entries
are ``{verb = "<keyword>"}`` (resolved like sentence verbs) or
``{inventory = {room, name[, id]}[, offset = <int>]}`` (resolved like ``obj``;
``offset`` shifts the clicked slot, see docs/plan.md C4).

A template may also carry ``override_choose`` (answers for menus inside a
cutscene override region, expected only when that cutscene plays) and
``no_skip = true`` (no cutscene skip during the step); both are omitted from
the output at their defaults (C4, Phase 8).
"""

import json
import string
import tomllib
from collections.abc import Iterable, Mapping
from pathlib import Path

from speedrun.conditions import MAX_ACTOR, ConditionError, parse_conditions
from speedrun.planner import Plan

# override_choose and no_skip are optional: omitted when empty / false (docs/plan.md C4).
C4_KEYS = ("action", "verb", "obj", "obj2", "room", "click", "choose", "override_choose", "until", "no_skip")
STEP_KEYS = frozenset({"verb", "obj", "obj2", "room", "click", "choose", "override_choose", "until", "no_skip"})
CLICK_KEYS = ("verb", "inventory")  # each click entry has exactly one of these
ACTION_KEYS = frozenset({"cite", "steps"})

_PADDING = "@" + string.whitespace


class CompileError(Exception):
    """Base class for every compiler error."""


class UnresolvedObject(CompileError):
    """An object reference matches nothing in ``objects.json``."""


class AmbiguousObject(CompileError):
    """An object name matches several objects in its room and no ``id`` was given."""

    def __init__(self, message: str, ids: Iterable[int]):
        super().__init__(message)
        self.ids = list(ids)


class UnknownVerb(CompileError):
    """A verb keyword is missing from ``[verbs]``, or its name is not a unique verb in the dump."""


class TemplateError(CompileError):
    """``steps.toml`` is malformed (bad key, type or condition)."""


class MissingStepTemplate(CompileError):
    """A plan action has no entry in ``steps.toml``."""

    def __init__(self, action: str):
        super().__init__(f"no step template for ground action {action!r} in steps.toml [actions]")
        self.action = action


def _is_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _clean(name: object) -> str:
    """Normalise a dump or template name: strip '@' padding and whitespace, casefold."""
    return name.strip(_PADDING).casefold() if isinstance(name, str) else ""


def _unique(ids: Iterable[int]) -> list[int]:
    return list(dict.fromkeys(ids))


class ObjectIndex:
    """Object and verb lookup over an ``objects.json`` dump (C6)."""

    def __init__(self, rooms: dict[int, list[tuple[int, str]]], verbs: list[tuple[int, str]]):
        self._rooms = rooms  # room -> [(object id, cleaned name)]
        self._verbs = verbs  # [(verb id, cleaned name)]

    @classmethod
    def from_dump(cls, path: Path) -> "ObjectIndex":
        with Path(path).open(encoding="utf-8") as f:
            return cls.from_dict(json.load(f))

    @classmethod
    def from_dict(cls, d: Mapping) -> "ObjectIndex":
        try:
            rooms: dict[int, list[tuple[int, str]]] = {}
            for room in d["rooms"]:
                if not _is_int(room["room"]):
                    raise TypeError(f"room number {room['room']!r} is not an int")
                objects = rooms.setdefault(room["room"], [])
                for obj in room.get("objects") or []:
                    if not _is_int(obj["id"]):
                        raise TypeError(f"object id {obj['id']!r} is not an int")
                    objects.append((obj["id"], _clean(obj.get("name"))))
            verbs = []
            for verb in d.get("verbs") or []:
                if not _is_int(verb["id"]):
                    raise TypeError(f"verb id {verb['id']!r} is not an int")
                verbs.append((verb["id"], _clean(verb.get("name"))))
        except (KeyError, TypeError, AttributeError) as e:
            raise CompileError(f"malformed objects.json: {e!r}") from e
        return cls(rooms, verbs)

    def resolve_object(self, ref: Mapping) -> int:
        """Resolve ``{room, name[, id]}`` or ``{actor}`` to an object id."""
        if not isinstance(ref, Mapping):
            raise TemplateError(f"object reference must be a table, got {ref!r}")
        keys = set(ref)
        if "actor" in keys:
            actor = ref["actor"]
            if keys != {"actor"} or not _is_int(actor) or not 0 < actor <= MAX_ACTOR:
                raise TemplateError(f"actor reference must be {{actor = 1..{MAX_ACTOR}}}, got {dict(ref)!r}")
            return actor

        if not {"room", "name"} <= keys <= {"room", "name", "id"}:
            raise TemplateError(f"object reference must be {{room, name[, id]}} or {{actor}}, got {dict(ref)!r}")
        room, name, oid = ref["room"], ref["name"], ref.get("id")
        if not _is_int(room) or not isinstance(name, str) or not _clean(name):
            raise TemplateError(f"object reference needs an int room and a non-empty name, got {dict(ref)!r}")
        if "id" in keys and not _is_int(oid):
            raise TemplateError(f"object reference id must be an int, got {dict(ref)!r}")

        if room not in self._rooms:
            raise UnresolvedObject(f"room {room} is not in objects.json (looking for {name!r})")
        objects = self._rooms[room]
        wanted = _clean(name)
        matches = _unique(i for i, n in objects if n == wanted)

        if oid is not None:
            if oid in matches:
                return oid
            actual = _unique(n for i, n in objects if i == oid)
            detail = f"id {oid} there is named {actual[0]!r}" if actual else f"no id {oid} there"
            raise UnresolvedObject(
                f"no object {oid} named {name!r} in room {room} ({detail}; ids named {name!r}: {matches})"
            )
        if len(matches) == 1:
            return matches[0]
        if not matches:
            names = sorted({n for _, n in objects if n})
            raise UnresolvedObject(f"no object named {name!r} in room {room} (room has: {', '.join(names)})")
        raise AmbiguousObject(
            f"object name {name!r} is ambiguous in room {room}: ids {matches}; add id = <one of them>",
            matches,
        )

    def verb_id(self, name: str) -> int:
        """Resolve a verb display name (e.g. ``"Walk to"``) to its unique verb id."""
        wanted = _clean(name)
        matches = _unique(i for i, n in self._verbs if n == wanted) if wanted else []
        if not matches:
            raise UnknownVerb(f"verb {name!r} is not in objects.json verbs")
        if len(matches) > 1:
            raise UnknownVerb(f"verb {name!r} is ambiguous in objects.json verbs: ids {matches}")
        return matches[0]


def resolve_verb(keyword: object, verbs: Mapping, objects: ObjectIndex) -> int:
    """Map a ``steps.toml`` verb keyword through ``[verbs]`` and the dump to a verb id."""
    if not isinstance(keyword, str):
        raise TemplateError(f"verb must be a keyword string, got {keyword!r}")
    if keyword not in verbs:
        raise UnknownVerb(f"verb keyword {keyword!r} is not in steps.toml [verbs]")
    name = verbs[keyword]
    if not isinstance(name, str):
        raise TemplateError(f"[verbs] {keyword} must map to a verb name string, got {name!r}")
    return objects.verb_id(name)


def load_steps(path: Path) -> dict:
    """Read ``steps.toml`` (C8). A missing, unreadable, non-UTF-8 or invalid file is a ``TemplateError``."""
    try:
        with Path(path).open("rb") as f:
            return tomllib.load(f)
    except (tomllib.TOMLDecodeError, UnicodeDecodeError, OSError) as e:
        raise TemplateError(f"{path}: {e}") from e


def _action_templates(entry: object) -> list:
    if not isinstance(entry, Mapping):
        raise TemplateError(f"entry must be a table with 'steps', got {entry!r}")
    unknown = set(entry) - ACTION_KEYS
    if unknown:
        raise TemplateError(f"unknown key(s) {sorted(unknown)}; allowed: {sorted(ACTION_KEYS)}")
    if "cite" in entry and not isinstance(entry["cite"], str):
        raise TemplateError(f"cite must be a string, got {entry['cite']!r}")
    templates = entry.get("steps")
    if not isinstance(templates, list) or not templates:
        raise TemplateError(f"'steps' must be a non-empty list of step tables, got {templates!r}")
    return templates


def _compile_click_entry(entry: object, verbs: Mapping, objects: ObjectIndex) -> dict:
    shape_ok = isinstance(entry, Mapping) and (
        set(entry) == {"verb"} or set(entry) == {"inventory"} or set(entry) == {"inventory", "offset"}
    )
    if not shape_ok:
        raise TemplateError(f"entry must be exactly {{verb = <keyword>}} or "
                            f"{{inventory = {{room, name[, id]}}[, offset = <int>]}}, got {entry!r}")
    if "verb" in entry:
        return {"verb": resolve_verb(entry["verb"], verbs, objects)}
    ref = entry["inventory"]
    if not isinstance(ref, Mapping) or "actor" in ref:
        raise TemplateError(f"inventory must be an object reference {{room, name[, id]}}, got {ref!r}")
    out = {"inventory": objects.resolve_object(ref)}
    if "offset" in entry:
        offset = entry["offset"]
        # Non-zero slot shift, e.g. -1 for the circus tent's off-by-one
        # (docs/part1/input-scripts.md); bool is an int subclass, so reject it explicitly.
        if type(offset) is not int or offset == 0:
            raise TemplateError(f"offset must be a non-zero int, got {offset!r}")
        out["offset"] = offset
    return out


def _compile_click(click: object, verbs: Mapping, objects: ObjectIndex) -> list[dict]:
    if not isinstance(click, list) or not click:
        raise TemplateError(f"click must be a non-empty list of click entries, got {click!r}")
    out = []
    for i, entry in enumerate(click):
        try:
            out.append(_compile_click_entry(entry, verbs, objects))
        except CompileError as e:
            _add_context(e, f"click[{i}]")
            raise
    return out


def _compile_step(action: str, tmpl: object, verbs: Mapping, objects: ObjectIndex) -> dict:
    if not isinstance(tmpl, Mapping):
        raise TemplateError(f"step must be a table, got {tmpl!r}")
    unknown = set(tmpl) - STEP_KEYS
    if unknown:
        raise TemplateError(f"unknown step key(s) {sorted(unknown)}; allowed: {sorted(STEP_KEYS)}")
    if "click" in tmpl:
        sentence = sorted({"verb", "obj", "obj2"} & set(tmpl))
        if sentence:
            raise TemplateError(f"a click step has no verb/obj/obj2, got click with {sentence}")

    step: dict = {"action": action}
    if "verb" in tmpl:
        step["verb"] = resolve_verb(tmpl["verb"], verbs, objects)
        if "obj" not in tmpl:
            raise TemplateError("a step with a verb needs an obj")
        step["obj"] = objects.resolve_object(tmpl["obj"])
        step["obj2"] = objects.resolve_object(tmpl["obj2"]) if "obj2" in tmpl else 0
    elif "obj" in tmpl or "obj2" in tmpl:
        raise TemplateError("obj/obj2 given without a verb")

    if "room" in tmpl:
        if not _is_int(tmpl["room"]):
            raise TemplateError(f"room must be an int, got {tmpl['room']!r}")
        step["room"] = tmpl["room"]

    if "click" in tmpl:
        step["click"] = _compile_click(tmpl["click"], verbs, objects)

    choose = _choices(tmpl, "choose")
    if "verb" not in step and "click" not in step and not choose:
        raise TemplateError("a step without a verb or click must answer a dialogue (non-empty choose)")
    step["choose"] = choose
    # Answers for menus inside a cutscene override region, used only when that
    # cutscene is played through (docs/part1/skips.md section 4.3).
    override_choose = _choices(tmpl, "override_choose")
    if override_choose:
        step["override_choose"] = override_choose

    try:
        step["until"] = parse_conditions(tmpl.get("until", []))
    except ConditionError as e:
        raise TemplateError(f"until: {e}") from e

    no_skip = tmpl.get("no_skip", False)
    if not isinstance(no_skip, bool):
        raise TemplateError(f"no_skip must be true or false, got {no_skip!r}")
    if no_skip:
        step["no_skip"] = True
    return step


def _choices(tmpl: Mapping, key: str) -> list[str]:
    """A ``choose``-style list: non-empty ASCII strings."""
    choices = tmpl.get(key, [])
    if not isinstance(choices, list) or not all(isinstance(c, str) and c for c in choices):
        raise TemplateError(f"{key} must be a list of non-empty strings, got {choices!r}")
    for c in choices:
        # The bridge matches against the game's raw text bytes, which are not Unicode (C5).
        if not c.isascii():
            raise TemplateError(
                f"{key} entry {c!r} is not ASCII; the bridge matches it against the game's raw "
                "text bytes, so use an ASCII substring of the choice (docs/plan.md C5)"
            )
    return list(choices)


def _add_context(e: CompileError, where: str) -> None:
    if e.args and isinstance(e.args[0], str):
        e.args = (f"{where}: {e.args[0]}", *e.args[1:])


def compile_plan(plan: Plan, steps: dict, objects: ObjectIndex) -> list[dict]:
    """Expand every plan action through its ``steps.toml`` template into C4 step dicts."""
    verbs = steps.get("verbs", {})
    actions = steps.get("actions", {})
    if not isinstance(verbs, Mapping) or not isinstance(actions, Mapping):
        raise TemplateError("steps.toml [verbs] and [actions] must be tables")

    out: list[dict] = []
    for ground in plan.actions:
        action = " ".join(ground)
        if action not in actions:
            raise MissingStepTemplate(action)
        try:
            templates = _action_templates(actions[action])
        except CompileError as e:
            _add_context(e, f"steps.toml action {action!r}")
            raise
        for i, tmpl in enumerate(templates):
            try:
                out.append(_compile_step(action, tmpl, verbs, objects))
            except CompileError as e:
                _add_context(e, f"action {action!r} step {i}")
                raise
    return out


def write_jsonl(steps: list[dict], path: Path) -> None:
    """Write one compact JSON object per line, creating parent directories.

    The file is written beside ``path`` and renamed over it, so a failure (or
    an interrupt) leaves the previous file intact and a reader never sees half a plan.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    try:
        with tmp.open("w", encoding="utf-8") as f:
            for step in steps:
                f.write(json.dumps(step, separators=(",", ":")) + "\n")
        tmp.replace(path)
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise
