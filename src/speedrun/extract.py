"""Merge extracted PDDL fragments into one model and compile its plans (Phase 7).

The fragments (format: ``speedrun.citations``) are ground actions over atoms
that name engine state, so merging is mechanical:

- the domain is every action, verbatim with its annotations, under the
  ``astar(lmcut())``-safe requirements, with ``:predicates`` collected from
  what the actions and the goal use;
- the problem's ``:init`` is read off a real segment-start state dump (C7
  ``state-start.json``): an atom is in it exactly when it holds there, and
  only atoms the domain mentions are listed;
- the goal is the segment's C3 goal (``segment.toml``) in the same atoms.

``compile_extracted`` turns a plan over those actions into C4 plan-player steps
from the annotations alone, so an extracted plan replays in the real engine.
"""

import json
from collections.abc import Iterable, Mapping
from pathlib import Path

from speedrun.citations import (
    ATOM_KINDS,
    FOREST_ROOMS,
    REQUIREMENTS,
    Action,
    Click,
    Sentence,
    check_fragments,
    parse_atom,
    parse_fragment,
)
from speedrun.conditions import ConditionError, parse_condition
from speedrun.planner import Plan

MERGED_FILES = frozenset({"domain.pddl", "problem.pddl"})  # written next to the fragments by extract-merge
VAR_ROOM = 4  # forest steps wait on VAR_ROOM, not a room check (docs/part1/model.md section 6)
_STATE_KEYS = {"room": int, "vars": list, "bits_set": list, "inventory": list, "owners": dict, "states": dict}


class ExtractError(Exception):
    """Fragments, a state dump or a goal that cannot be merged or compiled."""


def load_fragments(directory: Path) -> dict[str, str]:
    """``{file name: text}`` of every fragment in ``directory``, sorted, without the merged model."""
    d = Path(directory)
    if not d.is_dir():
        return {}
    return {p.name: p.read_text(encoding="utf-8") for p in sorted(d.glob("*.pddl")) if p.name not in MERGED_FILES}


def _as_mapping(fragments: Mapping[str, str] | Iterable[str]) -> dict[str, str]:
    if isinstance(fragments, Mapping):
        return dict(fragments)
    return {f"fragment-{i}": text for i, text in enumerate(fragments, 1)}


def sourced_actions(fragments: Mapping[str, str] | Iterable[str]) -> list[tuple[str, Action]]:
    """``(fragment, action)`` for every action of accepted fragments, in order.

    Raises ``ExtractError`` on any issue ``check_fragments`` finds without the
    script dump: filter the fragments (``citations.filter_fragments``) first.
    """
    frags = _as_mapping(fragments)
    issues = check_fragments(frags, None)
    if issues:
        lines = "\n".join(f"  {i}" for i in issues)
        raise ExtractError(f"the fragments have issues (filter them first, see `speedrun extract-check`):\n{lines}")
    return [(src, act) for src, text in frags.items() for act in parse_fragment(text, src).actions]


# --- goal --------------------------------------------------------------------------------


def _condition_literal(cond: dict) -> tuple[bool, str]:
    if "not" in cond:
        positive, name = _condition_literal(cond["not"])
        return not positive, name
    if "bit" in cond:
        if cond["eq"] not in (0, 1):
            raise ExtractError(f"condition {cond}: a bit is 0 or 1")
        return cond["eq"] == 1, f"bit-{cond['bit']}"
    if "var" in cond:
        name = f"var-{cond['var']}-eq-{cond['eq']}"
    elif "room" in cond:
        name = f"at-r{cond['room']}"
    elif "has" in cond:
        name = f"has-o{cond['has']}"
    elif "owner" in cond:
        name = f"owner-o{cond['owner']}-{cond['eq']}"
    elif "state" in cond:
        name = f"state-o{cond['state']}-{cond['eq']}"
    else:
        raise ExtractError(f"condition {cond} has no atom in the extraction vocabulary")
    if parse_atom(name) is None:
        raise ExtractError(f"condition {cond} gives ({name}), which is outside the extraction vocabulary")
    return True, name


def goal_literals(goal: Iterable[Mapping]) -> list[tuple[bool, str]]:
    """C3 conditions (``segment.toml`` ``goal``) as ``(positive, atom)`` literals."""
    out = []
    for cond in goal:
        try:
            parsed = parse_condition(cond)
        except ConditionError as e:
            raise ExtractError(f"goal condition {cond!r}: {e}") from e
        out.append(_condition_literal(parsed))
    return out


# --- init from the state dump --------------------------------------------------------------


def _load_state(state: Mapping | Path) -> Mapping:
    if isinstance(state, Path):
        try:
            state = json.loads(state.read_text(encoding="utf-8"))
        except (OSError, ValueError) as e:
            raise ExtractError(f"cannot read the state dump {state}: {e}") from e
    if not isinstance(state, Mapping):
        raise ExtractError(f"the state dump must be a JSON object (C7), got {type(state).__name__}")
    for key, kind in _STATE_KEYS.items():
        if not isinstance(state.get(key), kind):
            raise ExtractError(f"the state dump has no {kind.__name__} {key!r} (C7 state-start.json)")
    return state


def _holds(name: str, state: Mapping, errors: list[str]) -> bool:
    kind, args = parse_atom(name)
    if kind == "at":
        return state["room"] == args[0]
    if kind == "has":
        return args[0] in state["inventory"]
    if kind == "bit":
        return args[0] in state["bits_set"]
    if kind in ("state", "owner"):
        table = state["states" if kind == "state" else "owners"]
        if str(args[0]) not in table:
            errors.append(f"({name}): object {args[0]} has no {kind} in the state dump")
            return False
        return table[str(args[0])] == args[1]
    if kind == "class":
        return args[1] in (state.get("classes") or {}).get(str(args[0]), [])
    variables = state["vars"]
    if not 0 <= args[0] < len(variables):
        errors.append(f"({name}): var {args[0]} is outside the state dump's {len(variables)} vars")
        return False
    value = variables[args[0]]
    return value == args[1] if kind == "var-eq" else value >= args[1]


def _atom_key(name: str) -> tuple:
    kind, args = parse_atom(name)
    return ATOM_KINDS.index(kind), args


# --- merge -------------------------------------------------------------------------------------


def _literal_text(positive: bool, name: str) -> str:
    return f"({name})" if positive else f"(not ({name}))"


def _indent(text: str, prefix: str = "  ") -> str:
    return "\n".join(prefix + line if line.strip() else "" for line in text.splitlines())


def merge(
    fragments: Mapping[str, str] | Iterable[str],
    state: Mapping | Path,
    goal: Iterable[Mapping],
    *,
    name: str = "extracted",
) -> tuple[str, str]:
    """``(domain text, problem text)`` from accepted fragments, a C7 state dump and a C3 goal."""
    sourced = sourced_actions(fragments)
    actions = [act for _, act in sourced]
    if not actions:
        raise ExtractError("no actions to merge: every fragment is empty")
    state = _load_state(state)
    goal_lits = goal_literals(goal)

    used = {atom for act in actions for _, atom in (*act.pre, *act.eff)} | {atom for _, atom in goal_lits}
    predicates = sorted(used, key=_atom_key)
    errors: list[str] = []
    init = [p for p in predicates if _holds(p, state, errors)]
    if errors:
        raise ExtractError("atoms the state dump cannot evaluate:\n" + "\n".join(f"  {e}" for e in errors))

    parts = [
        ";; Merged from extracted fragments by `speedrun extract-merge`; edit the fragments, not this file.",
        f"(define (domain {name})",
        f"  (:requirements {' '.join(REQUIREMENTS)})",
        "  (:predicates",
        *(f"    ({p})" for p in predicates[:-1]),
        f"    ({predicates[-1]}))",
        "  (:functions (total-cost) - number)",
    ]
    by_source: dict[str, list[Action]] = {}
    for src, act in sourced:
        by_source.setdefault(src, []).append(act)
    for src, acts in by_source.items():
        parts += ["", f"  ;; ---- fragment {src}", ""]
        parts.append("\n\n".join(_indent(act.text) for act in acts))
    parts[-1] += ")"
    domain = "\n".join(parts) + "\n"

    goal_text = " ".join(_literal_text(*lit) for lit in goal_lits)
    room, tick = state.get("room"), state.get("tick")
    problem = "\n".join([
        f";; Init from the segment-start state dump (room {room}, tick {tick}): the domain's atoms that hold there.",
        f"(define (problem {name}-problem)",
        f"  (:domain {name})",
        "  (:init",
        *(f"    ({p})" for p in init),
        "    (= (total-cost) 0))",
        f"  (:goal (and {goal_text}))",
        "  (:metric minimize (total-cost)))",
    ]) + "\n"  # fmt: skip
    return domain, problem


# --- compile ---------------------------------------------------------------------------------


def action_step(act: Action) -> dict:
    """The C4 step that performs ``act``, from its annotations (key order as in C4)."""
    step: dict = {"action": act.name}
    inp = act.input
    if isinstance(inp, Sentence):
        step.update(verb=inp.verb, obj=inp.obj, obj2=inp.obj2)
    forest = act.room in FOREST_ROOMS
    if not forest:
        step["room"] = act.room
    if isinstance(inp, Click):
        slot = {"inventory": inp.inventory} | ({"offset": inp.offset} if inp.offset else {})
        step["click"] = [{"verb": inp.verb}, slot]
    step["choose"] = list(act.dialogue)
    step["until"] = [{"var": VAR_ROOM, "eq": act.room}] if forest else []
    return step


def compile_extracted(plan: Plan | Iterable, fragments: Mapping[str, str] | Iterable[str]) -> list[dict]:
    """C4 steps for every action of ``plan`` (a ``Plan`` or its action tuples), one step per action."""
    by_name = {act.name: act for _, act in sourced_actions(fragments)}
    ground = plan.actions if isinstance(plan, Plan) else plan
    steps = []
    for entry in ground:
        parts = (entry,) if isinstance(entry, str) else tuple(entry)
        if len(parts) != 1:
            raise ExtractError(f"plan action {' '.join(parts)!r} has arguments; extracted actions are 0-ary")
        name = parts[0].lower()
        if name not in by_name:
            raise ExtractError(f"plan action {name!r} is not in the extracted fragments")
        steps.append(action_step(by_name[name]))
    return steps
