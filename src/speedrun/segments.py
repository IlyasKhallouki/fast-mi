"""Load ``pddl/<segment>/segment.toml`` (contract C9)."""

import tomllib
from dataclasses import dataclass
from pathlib import Path

from speedrun import paths
from speedrun.conditions import ConditionError, parse_conditions


class SegmentError(Exception):
    """``segment.toml`` is missing or does not satisfy C9."""


@dataclass(frozen=True)
class Segment:
    name: str
    dir: Path
    domain: Path
    problem: Path
    steps: Path
    start: list[dict]  # C3 conjunction
    goal: list[dict]  # C3 conjunction, non-empty
    goal_cite: list[str]  # one citation per goal condition
    randomized_vars: list[dict]  # [{"var": N, "cite": "..."}]
    # {"verb_first", "count", "var_first", "cite"}: inventory slot verb verb_first+k
    # shows the object in Var[var_first+k]. SPEEDRUN_INVENTORY (C1) is this minus cite.
    inventory: dict | None = None


def _str(data: dict, key: str, default: str, where: Path) -> str:
    value = data.get(key, default)
    if not isinstance(value, str) or not value:
        raise SegmentError(f"{where}: {key!r} must be a non-empty string, got {value!r}")
    return value


def _conditions(data: dict, key: str, where: Path) -> list[dict]:
    try:
        return parse_conditions(data.get(key, []))
    except ConditionError as e:
        raise SegmentError(f"{where}: {key}: {e}") from e


def _randomized_vars(value: object, where: Path) -> list[dict]:
    if not isinstance(value, list):
        raise SegmentError(f"{where}: randomized_vars must be a list, got {value!r}")
    out = []
    for i, entry in enumerate(value):
        ok = (
            isinstance(entry, dict)
            and set(entry) == {"var", "cite"}
            and isinstance(entry["var"], int)
            and not isinstance(entry["var"], bool)
            and isinstance(entry["cite"], str)
            and entry["cite"]
        )
        if not ok:
            raise SegmentError(
                f"{where}: randomized_vars[{i}] must be {{var = <int>, cite = <string>}}, got {entry!r}"
            )
        out.append({"var": entry["var"], "cite": entry["cite"]})
    return out


_INVENTORY_INTS = ("verb_first", "count", "var_first")


def _inventory(value: object, where: Path) -> dict | None:
    if value is None:
        return None
    form = "{verb_first = <int >= 0>, count = <int >= 1>, var_first = <int >= 0>, cite = <string>}"
    ok = (
        isinstance(value, dict)
        and set(value) == {*_INVENTORY_INTS, "cite"}
        and all(isinstance(value[k], int) and not isinstance(value[k], bool) for k in _INVENTORY_INTS)
        and value["verb_first"] >= 0
        and value["count"] >= 1
        and value["var_first"] >= 0
        and isinstance(value["cite"], str)
        and value["cite"]
    )
    if not ok:
        raise SegmentError(f"{where}: inventory must be {form}, got {value!r}")
    return {**{k: value[k] for k in _INVENTORY_INTS}, "cite": value["cite"]}


def load_segment(name: str, base: Path = paths.PDDL_DIR) -> Segment:
    seg_dir = Path(base) / name
    toml_path = seg_dir / "segment.toml"
    if not toml_path.is_file():
        raise SegmentError(f"segment {name!r}: {toml_path} not found")
    try:
        with toml_path.open("rb") as f:
            data = tomllib.load(f)
    except tomllib.TOMLDecodeError as e:
        raise SegmentError(f"{toml_path}: {e}") from e

    start = _conditions(data, "start", toml_path)
    goal = _conditions(data, "goal", toml_path)
    if not goal:
        raise SegmentError(f"{toml_path}: goal is missing or empty")

    goal_cite = data.get("goal_cite", [])
    if not isinstance(goal_cite, list) or not all(isinstance(c, str) and c for c in goal_cite):
        raise SegmentError(f"{toml_path}: goal_cite must be a list of non-empty strings")
    if len(goal_cite) != len(goal):
        raise SegmentError(
            f"{toml_path}: goal_cite has {len(goal_cite)} entries but goal has {len(goal)}; "
            "every goal condition needs exactly one citation"
        )

    return Segment(
        name=_str(data, "name", name, toml_path),
        dir=seg_dir,
        domain=seg_dir / _str(data, "domain", "domain.pddl", toml_path),
        problem=seg_dir / _str(data, "problem", "problem.pddl", toml_path),
        steps=seg_dir / _str(data, "steps", "steps.toml", toml_path),
        start=start,
        goal=goal,
        goal_cite=list(goal_cite),
        randomized_vars=_randomized_vars(data.get("randomized_vars", []), toml_path),
        inventory=_inventory(data.get("inventory"), toml_path),
    )
