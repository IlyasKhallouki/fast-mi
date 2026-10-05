"""The position-keyed timed model: action costs that depend on where ego stands (Phase 8).

A pooled mean per action misprices orderings by hundreds of ticks, because a
walk's duration depends on the spot the previous action left ego on
(``speedrun.positions``). ``keyed_model`` rewrites the domain and problem so
Fast Downward tracks that spot and charges each action by it, with the
encoding recommended in ``docs/research/fd-costs.md`` §4(b), extended from
entry rooms to position tokens (§3.4, "spot"):

- a type ``pos``, one constant per position token (``p_start``,
  ``p_entry_<from>_<to>``, ``p_obj_<room>_<id>``, ``p_any``);
- ``(ego-pos ?p - pos)``: exactly one is true; static ``(pos-in-room ?p ?r)``
  (the token can be the position while ego is in ``?r``) and
  ``(link-entry ?from ?to ?p)`` (the token a ``walk ?from ?to`` leaves);
- every action in a keyed room gets a last parameter ``?ctx - pos`` with
  ``(ego-pos ?ctx) (pos-in-room ?ctx <room>)`` in its precondition. An action
  that moves ego adds ``(not (ego-pos ?ctx)) (ego-pos <anchor>)``; the generic
  walk gets ``?ctx ?next - pos`` and ``(link-entry ?from ?to ?next)``.
  Every deleted ``ego-pos`` fact is one the precondition requires, so
  ``ego-pos`` stays one multi-valued SAS variable, and the model stays in the
  lmcut-safe subset (no conditional effects, no quantifiers);
- ``speedrun.costing.apply_costs`` then turns each such action's cost into a
  function of all its parameters, with one ``:init`` value per ground
  instance (``apply_keyed_costs``). Its checks apply unchanged: every
  instance the static preconditions admit has a value (Fast Downward silently
  drops one without), and the summed costs stay far below the 30-bit g limit.

**Selective keying.** ``keyed_rooms`` limits the tracking to some rooms. In
every other room the position is the single token ``any``: their actions
keep their constant (pooled) cost, a walk *into* a keyed room sets the entry
token from ``(ego-pos any)``, and a walk out of one resets it to ``any``.
Ground operators and states then grow only inside the keyed rooms (fd-costs
§3.3).

**Plans.** Fast Downward prints the extra arguments
(``(walk dock lookout p_start p_entry_dock_lookout)``); ``KeyedModel.strip``
drops them so plans map back to ``steps.toml`` keys, and ``KeyedModel.split``
maps a ground instance to its ``(action, context)`` pair.
"""

from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass

from speedrun.costing import (
    ANY,
    CostingError,
    _after_head,
    _apply_edits,
    _Atom,
    _atom_args,
    _init,
    _List,
    _parse,
    _section,
    _typed_list,
    _typed_text,
    apply_costs,
    ground_costs,
)
from speedrun.planner import Plan
from speedrun.positions import AT, START, Positions, pddl_name

POS_TYPE = "pos"
CTX, NEXT = "?ctx", "?next"
PREDICATES = ("ego-pos", "pos-in-room", "link-entry")


@dataclass(frozen=True)
class KeyedModel:
    """A keyed domain and problem (costs as in the input) and how to read its ground actions."""

    domain: str
    problem: str
    positions: Positions
    keyed_rooms: frozenset[str]
    arity: dict[str, int]  # action schema -> its parameter count in the original model
    keyed: frozenset[str]  # schemas that read the context
    names: dict[str, str]  # PDDL object name -> position token

    def split(self, ground: str) -> tuple[str, str | None]:
        """``"walk a b p_start p_entry_a_b"`` -> ``("walk a b", "start")``; unkeyed: ``(action, None)``."""
        parts = ground.lower().split()
        if not parts or parts[0] not in self.arity:
            raise CostingError(f"{ground!r} is not a ground action of the keyed model")
        n = self.arity[parts[0]]
        base, extra = " ".join(parts[: 1 + n]), parts[1 + n :]
        if parts[0] not in self.keyed:
            if extra:
                raise CostingError(f"{ground!r}: unexpected arguments {extra} for an unkeyed action")
            return base, None
        if not extra or extra[0] not in self.names:
            raise CostingError(f"{ground!r}: no position argument")
        return base, self.names[extra[0]]

    def strip(self, plan: Plan) -> Plan:
        """The plan with the position arguments dropped: its actions are ``steps.toml`` keys again."""
        actions = []
        for action in plan.actions:
            if not action or action[0] not in self.arity:
                raise CostingError(f"plan action {action!r} is not in the keyed model")
            actions.append(tuple(action[: 1 + self.arity[action[0]]]))
        return Plan(actions=actions, cost=plan.cost)

    def pairs(self, actions: Sequence[str]) -> list[tuple[str, str]]:
        """Each plan action with the context the keyed model charges it in (``any`` if unkeyed)."""
        return keyed_pairs(self.positions, actions, self.keyed_rooms)


def keyed_pairs(positions: Positions, actions: Sequence[str], keyed_rooms: Iterable[str]) -> list[tuple[str, str]]:
    """Each plan action with the context a model keyed on ``keyed_rooms`` charges it in.

    An action is keyed when the room it runs in is keyed (a walk: the room it
    leaves); room-agnostic actions never are. Unkeyed actions get ``any``.
    """
    rooms = set(keyed_rooms)
    contexts = positions.contexts(actions)
    return [(a, c if positions.anchor(a).room in rooms else ANY) for a, c in zip(actions, contexts)]


# --- the rewrite -------------------------------------------------------------------------


@dataclass
class _Form:
    name: str
    params: list[tuple[str, str]]
    params_list: _List
    precondition: _List | None
    effect: _List


def _forms(domain: _List) -> list[_Form]:
    out = []
    for form in domain.lists():
        if form.head != ":action":
            continue
        name = form.items[1].text.lower()
        fields: dict[str, object] = {}
        for key, value in zip(form.items[2::2], form.items[3::2]):
            if isinstance(key, _Atom):
                fields[key.text.lower()] = value
        params = fields.get(":parameters")
        effect = fields.get(":effect")
        pre = fields.get(":precondition")
        if not isinstance(params, _List) or not isinstance(effect, _List):
            raise CostingError(f"action {name}: needs a :parameters list and an :effect")
        out.append(_Form(name, _typed_list(params.items, f"action {name}"), params, pre if isinstance(pre, _List) else
                         None, effect))  # fmt: skip
    return out


def _at_args(expr: _List | None) -> list[str]:
    """The arguments of the positive ``(at x)`` conjuncts of a precondition or effect."""
    if expr is None:
        return []
    conjuncts = expr.lists() if expr.head == "and" else [expr]
    return [(_atom_args(c) or ["?"])[0] for c in conjuncts if c.head == AT]


def _insert(text: str, lst: _List | None, extra: str, keyword_at: int | None = None) -> tuple[int, int, str]:
    """An edit that conjoins ``extra`` into ``lst`` (an ``and`` gets it before its ``)``)."""
    if lst is None:
        assert keyword_at is not None
        return keyword_at, keyword_at, f"\n    :precondition (and {extra})"
    if lst.head == "and":
        return lst.end - 1, lst.end - 1, " " + extra
    return lst.start, lst.end, f"(and {text[lst.start:lst.end]} {extra})"


def _check_free(names: Iterable[str], taken: set[str], what: str) -> None:
    clash = sorted(set(names) & taken)
    if clash:
        raise CostingError(f"keyed model: {what} {', '.join(clash)} already exist(s) in the model")


def keyed_model(
    domain_text: str, problem_text: str, positions: Positions, keyed_rooms: Iterable[str] | None = None
) -> KeyedModel:
    """The keyed domain and problem (see the module doc); ``keyed_rooms`` None keys every room."""
    domain = _parse(domain_text, "domain")
    problem = _parse(problem_text, "problem")
    rooms = set(positions.rooms())
    keyed_rooms = frozenset(rooms if keyed_rooms is None else keyed_rooms)
    unknown = sorted(keyed_rooms - rooms)
    if unknown:
        raise CostingError(f"keyed rooms {unknown} are not rooms of the model")

    def target(token: str) -> str:
        """The token an anchor sets: itself in a keyed room, else ``any``."""
        return token if positions.room_of(token) in keyed_rooms else ANY

    tokens = [t for t in positions.tokens() if positions.room_of(t) in keyed_rooms]
    unkeyed = sorted(rooms - keyed_rooms)
    if unkeyed:
        tokens.append(ANY)
    names = {pddl_name(t): t for t in tokens}

    # Name clashes: the new type, constants, predicates and parameters must be fresh.
    types = _section(domain, ":types")
    if types is None:
        raise CostingError("domain: no (:types ...) section to add the pos type to")
    constants = _section(domain, ":constants")
    predicates = _section(domain, ":predicates")
    if predicates is None:
        raise CostingError("domain: no (:predicates ...) section")
    taken = {a.text.lower() for a in types.items[1:] if isinstance(a, _Atom)}
    _check_free([POS_TYPE], taken, "type")
    objects = {a.text.lower() for sec in (constants, _section(problem, ":objects")) if sec is not None
               for a in sec.items[1:] if isinstance(a, _Atom)}  # fmt: skip
    _check_free(names, objects, "constant(s)")
    _check_free(PREDICATES, {p.head for p in predicates.lists() if p.head}, "predicate(s)")

    edits: list[tuple[int, int, str]] = [(types.end - 1, types.end - 1, f" {POS_TYPE}")]
    decl = f"\n    {' '.join(names)} - {POS_TYPE}"
    if constants is not None:
        edits.append((constants.end - 1, constants.end - 1, decl))
    else:
        edits.append((types.end, types.end, f"\n  (:constants{decl})"))
    edits.append((predicates.end - 1, predicates.end - 1,
                   "\n    (ego-pos ?p - pos)                   ; ego's position token (exactly one)"
                   "\n    (pos-in-room ?p - pos ?r - room)     ; static: ?p can be the position while ego is in ?r"
                   "\n    (link-entry ?from ?to - room ?p - pos)"
                   " ; static: the position (walk ?from ?to) leaves\n  "))  # fmt: skip

    arity: dict[str, int] = {}
    keyed: set[str] = set()
    links: list[tuple[str, str, str]] = []
    by_schema: dict[str, list[str]] = {}
    for action in positions.actions():
        by_schema.setdefault(action.split()[0], []).append(action)
    for form in _forms(domain):
        arity[form.name] = len(form.params)
        ground = by_schema.get(form.name, [])
        variables = {v for v, _ in form.params}
        _check_free([CTX, NEXT], variables, "parameter(s)")
        pre_at, add_at = _at_args(form.precondition), _at_args(form.effect)
        kw = form.params_list.end  # where a missing :precondition goes
        if form.params:
            # Only the generic room change is supported: (at ?from) -> (at ?to), both parameters.
            if len(pre_at) != 1 or len(add_at) != 1 or not {pre_at[0], add_at[0]} <= variables:
                raise CostingError(f"action {form.name}: keyed costs support parameters only for a generic "
                                   "walk with (at ?from) in its precondition and (at ?to) in its effect")  # fmt: skip
            frm, to = pre_at[0], add_at[0]
            for g in ground:
                anchor = positions.anchor(g)
                if anchor.to is None:
                    raise CostingError(f"{g}: expected a room change")
                links.append((anchor.room, anchor.to, target(anchor.token)))
            new_params = form.params + [(CTX, POS_TYPE), (NEXT, POS_TYPE)]
            edits.append((form.params_list.start, form.params_list.end, f"({_typed_text(new_params)})"))
            edits.append(_insert(domain_text, form.precondition,
                                 f"(ego-pos {CTX}) (pos-in-room {CTX} {frm}) (link-entry {frm} {to} {NEXT})", kw))
            edits.append(_insert(domain_text, form.effect, f"(not (ego-pos {CTX})) (ego-pos {NEXT})"))
            keyed.add(form.name)
            continue
        if not ground:
            raise CostingError(f"action {form.name}: not among the derived positions (stale positions?)")
        anchor = positions.anchor(form.name)
        if anchor.room is None:
            continue  # room-agnostic (inventory only): never keyed, never moves ego
        if anchor.room in keyed_rooms:
            edits.append((form.params_list.start, form.params_list.end, f"({CTX} - {POS_TYPE})"))
            edits.append(_insert(domain_text, form.precondition, f"(ego-pos {CTX}) (pos-in-room {CTX} {anchor.room})",
                                 kw))  # fmt: skip
            if anchor.token is not None:
                to = pddl_name(target(anchor.token))
                edits.append(_insert(domain_text, form.effect, f"(not (ego-pos {CTX})) (ego-pos {to})"))
            keyed.add(form.name)
        elif anchor.token is not None and target(anchor.token) != ANY:
            # From an unkeyed room into a keyed one: the position was "any".
            any_ = pddl_name(ANY)
            edits.append(_insert(domain_text, form.precondition, f"(ego-pos {any_})", kw))
            edits.append(_insert(domain_text, form.effect,
                                 f"(not (ego-pos {any_})) (ego-pos {pddl_name(anchor.token)})"))  # fmt: skip
    missing = sorted(set(by_schema) - set(arity))
    if missing:
        raise CostingError(f"positions name actions the domain lacks: {missing}")

    where = "every room" if not unkeyed else (
        f"{', '.join(sorted(keyed_rooms)) or 'no room'}; elsewhere it is {pddl_name(ANY)}")
    header = (";; KEYED COPY written by speedrun.keyed (do not edit): ego's position token\n"
              f";; (ego-pos) is tracked in {where}.\n")  # fmt: skip
    keyed_domain = header + _apply_edits(domain_text, edits)

    initial = START if positions.initial_room in keyed_rooms else ANY
    facts = [f"(ego-pos {pddl_name(initial)})"]
    facts += [f"(pos-in-room {pddl_name(t)} {positions.room_of(t)})" for t in tokens if t != ANY]
    facts += [f"(pos-in-room {pddl_name(ANY)} {r})" for r in unkeyed]
    facts += [f"(link-entry {a} {b} {pddl_name(t)})" for a, b, t in sorted(set(links))]
    init = _init(problem)
    at, tail = _after_head(problem_text, init.items[0])
    block = "\n    ;; Position keying (speedrun.keyed): ego's position, and where each token can be.\n"
    block += "\n".join(f"    {f}" for f in facts) + tail
    keyed_problem = header + _apply_edits(problem_text, [(at, at, block)])
    return KeyedModel(keyed_domain, keyed_problem, positions, keyed_rooms, arity, frozenset(keyed), names)


def apply_keyed_costs(model: KeyedModel, cost: Callable[[str, str | None], float | None]) -> tuple[str, str]:
    """The timed keyed domain and problem: every ground instance costs ``cost(action, context)``.

    ``context`` is None for unkeyed actions. A None cost means unmeasured: 1 tick.
    """
    costs = {}
    for ground in ground_costs(model.domain, model.problem):
        value = cost(*model.split(ground))
        if value is not None:
            costs[ground] = value
    return apply_costs(model.domain, model.problem, costs, default_cost=1)

