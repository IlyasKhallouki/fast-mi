"""C3 condition objects: validation and JSON serialisation.

A condition is one of::

    {"var": N, "eq": V}    global variable N == V
    {"bit": N, "eq": V}    bit variable N == V
    {"owner": O, "eq": A}  object O's owner == A
    {"state": O, "eq": S}  object O's state == S
    {"room": R}            current room == R
    {"has": O}             ego's inventory contains object O
    {"not": <condition>}   negation

A list of conditions is a conjunction. The same shapes are used by
``segment.toml`` (``start``, ``goal``), ``steps.toml`` (``until``) and the plan
player, so parsing accepts any mapping (TOML tables and JSON objects alike) and
returns plain dicts.
"""

import json
from collections.abc import Mapping, Sequence

_COMPARE_KEYS = ("var", "bit", "owner", "state")  # {key: int, "eq": int}
_UNARY_KEYS = ("room", "has")  # {key: int}

_FORMS = "{var|bit|owner|state: int, eq: int}, {room: int}, {has: int} or {not: condition}"


class ConditionError(ValueError):
    """A value is not a valid C3 condition (or list of conditions)."""


def _int(cond: Mapping, key: str) -> int:
    value = cond[key]
    if not isinstance(value, int) or isinstance(value, bool):
        raise ConditionError(f"condition {dict(cond)!r}: {key!r} must be an int, got {value!r}")
    return value


def parse_condition(obj: Mapping) -> dict:
    """Validate one C3 condition and return it as a fresh plain dict of ints."""
    if not isinstance(obj, Mapping):
        raise ConditionError(f"a condition must be a table/object, got {obj!r}")
    keys = set(obj)
    if keys == {"not"}:
        try:
            return {"not": parse_condition(obj["not"])}
        except ConditionError as e:
            raise ConditionError(f"in 'not': {e}") from e
    for key in _COMPARE_KEYS:
        if keys == {key, "eq"}:
            return {key: _int(obj, key), "eq": _int(obj, "eq")}
    for key in _UNARY_KEYS:
        if keys == {key}:
            return {key: _int(obj, key)}
    raise ConditionError(f"invalid condition {dict(obj)!r}: expected one of {_FORMS}")


def parse_conditions(seq: Sequence[Mapping]) -> list[dict]:
    """Validate a conjunction (a list of C3 conditions)."""
    if not isinstance(seq, (list, tuple)):
        raise ConditionError(f"conditions must be a list, got {seq!r}")
    out = []
    for i, cond in enumerate(seq):
        try:
            out.append(parse_condition(cond))
        except ConditionError as e:
            raise ConditionError(f"condition [{i}]: {e}") from e
    return out


def to_json(conds: Sequence[Mapping]) -> str:
    """Serialise a validated conjunction as compact JSON (e.g. for ``SPEEDRUN_START``)."""
    return json.dumps(parse_conditions(conds), separators=(",", ":"))
