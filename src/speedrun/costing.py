"""Measured action costs: the cost table, and timed copies of a domain and problem (Task 8.3).

**Cost table.** A ``CostTable`` maps each ground action string (the planner's
lower-case ``"name arg1 arg2"``, which is also the C4 ``action`` field) to its
measured tick samples, pooled from one or more ``speedrun measure`` summaries
(only runs that reached the goal contribute). It is saved as JSON
(``TABLE_VERSION`` 1), one action per line::

    {"version": 1, "unit": "ticks",
     "skips": {"text": true, "cutscenes": true},  # the setting every sample was measured with
     "engine": {"talkspeed": 255},                # the engine's timing pins, likewise
     "bridges": ["speedrun-bridge v1"],
     "actions": {
       "open-bar-door": {"n": 35, "mean": 354.0, "median": 354.0, "stdev": 0.0,
                         "min": 354, "max": 354, "cost": 354, "samples": [354, ...]}}}

``cost`` is the integer the planner gets: ``integer_cost(mean)``.

**Timed copies.** ``apply_costs`` rewrites the domain and problem text so
Fast Downward minimises measured ticks instead of the action count:

- a 0-ary action's ``(increase (total-cost) N)`` becomes its measured mean,
  rounded, and at least 1 (``integer_cost``). Unmeasured actions get
  ``default_cost``; 1 is a lower bound, since every action takes at least a tick;
- an action with parameters (``walk ?from ?to``) gets a static cost function
  ``(<name>-cost ?from ?to)``, declared in ``:functions``, and the problem's
  ``:init`` gets one ``(= (walk-cost a b) N)`` per ground instance;
- ground instances are the join of the action's positive *static*
  preconditions (predicates no action changes, e.g. ``(link ?from ?to)``)
  over the problem's ``:init``. A parameter that no static precondition binds
  is an error: the instances could not be enumerated.

Every value must be defined: Fast Downward's translator treats the cost
function's value as a reachability condition (``translate/normalize.py``),
so a ground action whose ``(= (f args) N)`` is missing from ``:init`` is
**silently dropped** from the task, not reported. Verified with
``build/downward/release`` on a toy: removing one ``(= (walk-cost c d) 5)``
made the planner pick a 200-cost drive over a cheaper walk route, exit 0.

The rewrite is text surgery on a comment-aware parse, so every comment and
``; src:`` citation stays where it was. Both outputs start with a
``;; TIMED COPY`` header. Costs are positive integers: lmcut needs integers,
and a zero-cost action could loop for free.
"""

import json
import math
import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path

from speedrun.measure import describe

TABLE_VERSION = 1

_TOKEN = re.compile(r";[^\n]*|\(|\)|[^\s();]+")
_INT = re.compile(r"^\d+$")
# Heads that are not predicates, in conditions and effects.
_LOGICAL = frozenset({"and", "or", "not", "imply", "exists", "forall", "when", "="})
_NUMERIC_EFFECTS = frozenset({"increase", "decrease", "assign", "scale-up", "scale-down"})


class CostingError(Exception):
    """The domain/problem cannot be costed, or a cost table is inconsistent."""


# Fast Downward keeps g in a 30-bit field (search_node_info.h:19): a path cost above
# 2**29 - 1 silently wraps and the planner returns a wrong plan with exit 0
# (docs/research/fd-costs.md §1). One action may cost at most MAX_ACTION_COST
# ticks (about 4.6 hours of game time), and the sum of every ground action's cost
# must stay below FD_COST_BUDGET, which leaves a 4x margin for plans that repeat
# actions.
MAX_ACTION_COST = 1_000_000
FD_COST_BUDGET = 2**27


def integer_cost(mean: float) -> int:
    """The planner's cost for a measured mean: rounded to an integer, and at least 1."""
    cost = max(1, round(mean))
    if cost > MAX_ACTION_COST:
        raise CostingError(
            f"cost {cost} ticks exceeds {MAX_ACTION_COST}: risks Fast Downward's 30-bit g overflow"
        )
    return cost


def check_cost_budget(costs) -> None:
    """Raise unless the summed costs stay safely inside Fast Downward's g range."""
    total = sum(costs)
    if total >= FD_COST_BUDGET:
        raise CostingError(
            f"summed action costs {total} >= {FD_COST_BUDGET}: a plan could overflow Fast Downward's g"
        )


# --- a comment-aware s-expression reader with source offsets -------------------------


@dataclass
class _Atom:
    text: str
    start: int
    end: int


@dataclass
class _List:
    items: list
    start: int  # offset of "("
    end: int  # offset just past ")"

    @property
    def head(self) -> str | None:
        first = self.items[0] if self.items else None
        return first.text.lower() if isinstance(first, _Atom) else None

    def lists(self) -> list["_List"]:
        return [x for x in self.items if isinstance(x, _List)]


def _parse(text: str, what: str) -> _List:
    stack: list[list] = [[]]
    starts: list[int] = []
    for m in _TOKEN.finditer(text):
        tok = m.group()
        if tok.startswith(";"):
            continue
        if tok == "(":
            stack.append([])
            starts.append(m.start())
        elif tok == ")":
            if len(stack) == 1:
                raise CostingError(f"{what}: unbalanced ')' at offset {m.start()}")
            items = stack.pop()
            stack[-1].append(_List(items, starts.pop(), m.end()))
        else:
            stack[-1].append(_Atom(tok, m.start(), m.end()))
    if len(stack) != 1:
        raise CostingError(f"{what}: unbalanced '(' (unclosed at offset {starts[-1]})")
    forms = [x for x in stack[0] if isinstance(x, _List)]
    if len(forms) != 1 or len(stack[0]) != 1:
        raise CostingError(f"{what}: expected exactly one (define ...) form")
    return forms[0]


def _section(tree: _List, key: str) -> _List | None:
    found = [x for x in tree.lists() if x.head == key]
    return found[0] if found else None


def _atom_args(lst: _List) -> list[str] | None:
    """``(pred a ?b)`` -> ``["a", "?b"]`` (lower case); None if an argument is not an atom."""
    args = lst.items[1:]
    if not all(isinstance(a, _Atom) for a in args):
        return None
    return [a.text.lower() for a in args]


# --- domain and problem structure -------------------------------------------------------


@dataclass
class _Action:
    name: str
    params: list[tuple[str, str]]  # (variable, type)
    precondition: _List | None
    effect: _List | None
    cost: _List  # the (increase (total-cost) X) term
    cost_value: object  # its X: an _Atom or a _List


def _typed_list(items: list, what: str) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    pending: list[str] = []
    k = 0
    while k < len(items):
        item = items[k]
        if not isinstance(item, _Atom):
            raise CostingError(f"{what}: unexpected {item!r} in a typed list")
        if item.text == "-":
            if k + 1 >= len(items) or not isinstance(items[k + 1], _Atom):
                raise CostingError(f"{what}: '-' without a type")
            out += [(v, items[k + 1].text.lower()) for v in pending]
            pending = []
            k += 2
            continue
        pending.append(item.text.lower())
        k += 1
    return out + [(v, "object") for v in pending]


def _cost_terms(effect: _List | None, inside: str | None = None) -> list[tuple[_List, str | None]]:
    """Every ``(increase (total-cost) X)`` in an effect, with the conditional head it sits in."""
    if effect is None:
        return []
    found = []
    head = effect.head
    if head == "increase":
        target = effect.items[1] if len(effect.items) > 1 else None
        if isinstance(target, _List) and target.head == "total-cost":
            found.append((effect, inside))
        return found
    for sub in effect.lists():
        found += _cost_terms(sub, inside or (head if head in ("when", "forall") else None))
    return found


def _actions(domain: _List) -> list[_Action]:
    out = []
    for form in domain.lists():
        if form.head != ":action":
            continue
        if len(form.items) < 2 or not isinstance(form.items[1], _Atom):
            raise CostingError("domain: an (:action ...) has no name")
        name = form.items[1].text.lower()
        fields: dict[str, object] = {}
        k = 2
        while k + 1 < len(form.items):
            key = form.items[k]
            if isinstance(key, _Atom) and key.text.startswith(":"):
                fields[key.text.lower()] = form.items[k + 1]
            k += 2
        params = fields.get(":parameters")
        param_list = _typed_list(params.items, f"action {name}") if isinstance(params, _List) else []
        pre = fields.get(":precondition")
        eff = fields.get(":effect")
        pre = pre if isinstance(pre, _List) else None
        eff = eff if isinstance(eff, _List) else None
        terms = _cost_terms(eff)
        if not terms:
            raise CostingError(
                f"action {name}: no (increase (total-cost) N) effect; under a metric it would cost 0"
            )
        if len(terms) > 1:
            raise CostingError(f"action {name}: {len(terms)} total-cost effects (Fast Downward allows one)")
        term, inside = terms[0]
        if inside is not None:
            raise CostingError(f"action {name}: its total-cost effect sits inside ({inside} ...)")
        if len(term.items) != 3:
            raise CostingError(f"action {name}: malformed total-cost effect")
        out.append(_Action(name, param_list, pre, eff, term, term.items[2]))
    return out


def _typed_text(params: list[tuple[str, str]]) -> str:
    """``[("?from", "room"), ("?to", "room")]`` -> ``"?from ?to - room"``."""
    groups: list[tuple[list[str], str]] = []
    for var, typ in params:
        if groups and groups[-1][1] == typ:
            groups[-1][0].append(var)
        else:
            groups.append(([var], typ))
    return " ".join(f"{' '.join(vs)} - {t}" for vs, t in groups)


def _effect_predicates(effect: _List | None) -> set[str]:
    if effect is None:
        return set()
    head = effect.head
    if head in _NUMERIC_EFFECTS:
        return set()
    if head in _LOGICAL:
        return {p for sub in effect.lists() for p in _effect_predicates(sub)}
    return {head} if head else set()


def _static_atoms(action: _Action, fluents: set[str]) -> list[tuple[str, list[str]]]:
    """Positive static precondition atoms at the top level of the precondition."""
    pre = action.precondition
    if pre is None:
        return []
    conjuncts = pre.lists() if pre.head == "and" else [pre]
    out = []
    for c in conjuncts:
        head = c.head
        if head is None or head in _LOGICAL or head in fluents:
            continue
        args = _atom_args(c)
        if args is not None:
            out.append((head, args))
    return out


def _init(problem: _List) -> _List:
    init = _section(problem, ":init")
    if init is None:
        raise CostingError("problem: no (:init ...) section")
    return init


def _init_facts(init: _List) -> dict[str, list[tuple[str, ...]]]:
    facts: dict[str, list[tuple[str, ...]]] = {}
    for fact in init.lists():
        head = fact.head
        if head is None or head == "=":
            continue
        args = _atom_args(fact)
        if args is not None:
            facts.setdefault(head, []).append(tuple(args))
    return facts


def _ground_instances(
    action: _Action, fluents: set[str], facts: Mapping[str, list[tuple[str, ...]]]
) -> list[tuple[str, ...]]:
    """Parameter tuples of the action's ground instances: the join of its static preconditions."""
    variables = [v for v, _ in action.params]
    static = _static_atoms(action, fluents)
    covered = {a for _, args in static for a in args if a.startswith("?")}
    missing = [v for v in variables if v not in covered]
    if missing:
        raise CostingError(
            f"action {action.name}: parameter(s) {', '.join(missing)} are not bound by a static "
            "precondition, so its ground instances cannot be enumerated for a cost function"
        )
    bindings: list[dict[str, str]] = [{}]
    for pred, args in static:
        joined = []
        for b in bindings:
            for fact in facts.get(pred, []):
                if len(fact) != len(args):
                    continue
                nb = dict(b)
                for arg, value in zip(args, fact):
                    if arg.startswith("?"):
                        if nb.setdefault(arg, value) != value:
                            break
                    elif arg != value:
                        break
                else:
                    joined.append(nb)
        bindings = joined
    return list(dict.fromkeys(tuple(b[v] for v in variables) for b in bindings))


def _function_names(domain: _List) -> set[str]:
    functions = _section(domain, ":functions")
    if functions is None:
        return set()
    return {f.head for f in functions.lists() if f.head}


def _predicate_names(domain: _List) -> set[str]:
    predicates = _section(domain, ":predicates")
    return {p.head for p in predicates.lists() if p.head} if predicates else set()


def _function_values(init: _List) -> dict[tuple[str, ...], int]:
    """``(= (f a b) N)`` facts in ``:init`` -> ``{("f", "a", "b"): N}``."""
    values = {}
    for fact in init.lists():
        if fact.head != "=" or len(fact.items) != 3:
            continue
        target, value = fact.items[1], fact.items[2]
        if isinstance(target, _List) and target.head and isinstance(value, _Atom) and _INT.match(value.text):
            args = _atom_args(target)
            if args is not None:
                values[(target.head, *args)] = int(value.text)
    return values


# --- apply_costs ---------------------------------------------------------------------


def _mean(value) -> float | None:
    if isinstance(value, Mapping):
        value = value.get("mean")
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise CostingError(f"a cost must be a finite number of ticks, got {value!r}")
    return float(value)


def _apply_edits(text: str, edits: list[tuple[int, int, str]]) -> str:
    for start, end, new in sorted(edits, key=lambda e: (e[0], e[1]), reverse=True):
        text = text[:start] + new + text[end:]
    return text


def _after_head(text: str, head: _Atom) -> tuple[int, str]:
    """Where to insert lines that open a section, and the text that keeps what follows intact."""
    line_end = text.find("\n", head.end)
    line_end = len(text) if line_end == -1 else line_end
    rest = text[head.end : line_end].strip()
    if not rest or rest.startswith(";"):
        return line_end, ""  # the head's line ends after it (maybe with a comment): new lines follow it
    return head.end, "\n    "  # facts follow the head on its line: they move to the next line


def _header(default_cost: int) -> str:
    return (
        ";; TIMED COPY written by speedrun.costing (do not edit): every action's\n"
        ";; (increase (total-cost) N) is its measured mean ticks, rounded and at least 1;\n"
        f";; unmeasured actions cost {default_cost}. Actions with parameters cost a static\n"
        ";; <action>-cost function, valued per ground instance in the problem's :init.\n"
    )


def apply_costs(
    domain_text: str,
    problem_text: str,
    costs: Mapping[str, float | Mapping],
    default_cost: int = 1,
) -> tuple[str, str]:
    """Return a timed copy of ``(domain_text, problem_text)``; see the module doc.

    ``costs`` maps ground action strings to mean ticks (or to cost-table
    entries with a ``"mean"``). Actions it does not name cost ``default_cost``.
    """
    if isinstance(default_cost, bool) or not isinstance(default_cost, int) or default_cost < 1:
        raise ValueError(f"default_cost must be a positive integer, got {default_cost!r}")
    domain = _parse(domain_text, "domain")
    problem = _parse(problem_text, "problem")
    if _section(problem, ":metric") is None:
        raise CostingError("problem: no (:metric minimize (total-cost)); Fast Downward would ignore every cost")
    requirements = _section(domain, ":requirements")
    if requirements is None or ":action-costs" not in {a.text.lower() for a in requirements.items[1:]}:
        raise CostingError("domain: :requirements lacks :action-costs")
    functions = _section(domain, ":functions")
    if functions is None:
        raise CostingError("domain: no (:functions (total-cost) - number) section")

    actions = _actions(domain)
    fluents = set().union(*(_effect_predicates(a.effect) for a in actions)) if actions else set()
    init = _init(problem)
    facts = _init_facts(init)
    taken = _function_names(domain) | _predicate_names(domain)

    def cost_of(ground: str) -> int:
        mean = _mean(costs.get(ground))
        return default_cost if mean is None else integer_cost(mean)

    domain_edits: list[tuple[int, int, str]] = []
    declarations: list[str] = []
    values: list[str] = []
    for action in actions:
        value = action.cost_value
        if not isinstance(value, _Atom) or not _INT.match(value.text):
            shown = domain_text[value.start : value.end] if hasattr(value, "start") else repr(value)
            raise CostingError(
                f"action {action.name}: its cost is {shown!r}, not an integer constant (already timed?)"
            )
        if not action.params:
            domain_edits.append((value.start, value.end, str(cost_of(action.name))))
            continue
        fname = f"{action.name}-cost"
        if fname in taken:
            raise CostingError(f"action {action.name}: the name {fname!r} is already a function or predicate")
        variables = [v for v, _ in action.params]
        typed = _typed_text(action.params)
        domain_edits.append((value.start, value.end, f"({fname} {' '.join(variables)})"))
        declarations.append(f"({fname} {typed}) - number")
        instances = _ground_instances(action, fluents, facts)
        for args in instances:
            values.append(f"(= ({fname} {' '.join(args)}) {cost_of(' '.join((action.name, *args)))})")

    close = functions.end - 1  # the section's ")"
    domain_edits += [(close, close, "".join(f"\n    {d}" for d in declarations))] if declarations else []
    timed_domain = _header(default_cost) + _apply_edits(domain_text, domain_edits)

    timed_problem = problem_text
    if values:
        at, tail = _after_head(problem_text, init.items[0])
        block = "\n    ;; Timed costs (speedrun.costing): one value per ground instance.\n"
        block += "\n".join(f"    {v}" for v in values) + tail
        timed_problem = _apply_edits(problem_text, [(at, at, block)])
    timed_problem = _header(default_cost) + timed_problem

    # Fast Downward drops a ground action whose cost value is missing, without a word:
    # make sure every instance got exactly one value.
    expected = sum(len(_ground_instances(a, fluents, facts)) for a in actions if a.params)
    defined = _function_values(_init(_parse(timed_problem, "timed problem")))
    timed_names = {d.split()[0].lstrip("(") for d in declarations}
    if sum(1 for key in defined if key[0] in timed_names) != expected:
        raise CostingError(f"internal: {expected} ground instances but a different number of cost values")
    check_cost_budget(ground_costs(timed_domain, timed_problem).values())
    return timed_domain, timed_problem


def ground_costs(domain_text: str, problem_text: str) -> dict[str, int]:
    """Every ground action's cost in a (timed or untimed) domain and problem.

    Parameterised actions are grounded like ``apply_costs`` does. A function
    cost without an ``:init`` value raises: Fast Downward would drop that action.
    """
    domain = _parse(domain_text, "domain")
    init = _init(_parse(problem_text, "problem"))
    actions = _actions(domain)
    fluents = set().union(*(_effect_predicates(a.effect) for a in actions)) if actions else set()
    facts = _init_facts(init)
    values = _function_values(init)
    out: dict[str, int] = {}
    for action in actions:
        instances = _ground_instances(action, fluents, facts) if action.params else [()]
        value = action.cost_value
        for args in instances:
            ground = " ".join((action.name, *args))
            if isinstance(value, _Atom) and _INT.match(value.text):
                out[ground] = int(value.text)
                continue
            if not isinstance(value, _List) or not value.head:
                raise CostingError(f"action {action.name}: unsupported cost term")
            mapping = dict(zip((v for v, _ in action.params), args))
            fargs = [mapping.get(a, a) for a in _atom_args(value) or []]
            key = (value.head, *fargs)
            if key not in values:
                raise CostingError(f"{ground}: no (= ({' '.join(key)}) N) in :init; Fast Downward would drop it")
            out[ground] = values[key]
    return out


def write_timed(
    domain: Path, problem: Path, costs: Mapping[str, float | Mapping], out_dir: Path, default_cost: int = 1
) -> tuple[Path, Path]:
    """Write ``out_dir/domain.pddl`` and ``out_dir/problem.pddl``, the timed copies of the given files."""
    timed_domain, timed_problem = apply_costs(
        Path(domain).read_text(encoding="utf-8"), Path(problem).read_text(encoding="utf-8"), costs, default_cost
    )
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = (out_dir / "domain.pddl", out_dir / "problem.pddl")
    for path, text in zip(paths, (timed_domain, timed_problem)):
        path.write_text(text, encoding="utf-8")
    return paths


# --- cost table --------------------------------------------------------------------------


class CostTable:
    """Measured tick samples per ground action, pooled from measure summaries."""

    def __init__(self) -> None:
        self._samples: dict[str, list[int]] = {}
        self.skips: dict | None = None
        self.engine: dict | None = None
        self.bridges: set[str] = set()

    @classmethod
    def from_summaries(cls, summaries: Iterable[dict]) -> "CostTable":
        table = cls()
        for summary in summaries:
            table.add_summary(summary)
        return table

    def add_summary(self, summary: dict) -> None:
        """Pool the instances of every run that reached the goal."""
        skips, engine = summary.get("skips"), summary.get("engine")
        if self.skips is not None and skips != self.skips:
            raise CostingError(
                f"cannot pool samples measured with skip settings {skips} into a table measured with {self.skips}"
            )
        if self.engine is not None and engine != self.engine:
            raise CostingError(
                f"cannot pool samples measured with engine settings {engine} into a table measured with {self.engine}"
            )
        self.skips, self.engine = skips, engine
        for run in summary.get("runs", []):
            if not run.get("ok"):
                continue
            if run.get("bridge"):
                self.bridges.add(run["bridge"])
            for instance in run.get("instances", []):
                self._samples.setdefault(instance["action"], []).append(int(instance["ticks"]))

    def actions(self) -> list[str]:
        return sorted(self._samples)

    def samples(self, action: str) -> list[int]:
        return list(self._samples.get(action, []))

    def measured(self, action: str) -> bool:
        return bool(self._samples.get(action))

    def mean(self, action: str) -> float | None:
        return describe(self._samples.get(action, []))["mean"]

    def means(self) -> dict[str, float]:
        return {a: self.mean(a) for a in self.actions()}

    def entry(self, action: str) -> dict:
        """n, mean, median, stdev, min, max (floats rounded to 3 places), the planner's cost, and the samples."""
        stats = describe(self._samples.get(action, []))
        cost = None if stats["mean"] is None else integer_cost(stats["mean"])
        rounded = {k: round(v, 3) if isinstance(v, float) else v for k, v in stats.items()}
        return {**rounded, "cost": cost, "samples": self.samples(action)}

    def to_json(self) -> dict:
        return {
            "version": TABLE_VERSION,
            "unit": "ticks",
            "skips": self.skips,
            "engine": self.engine,
            "bridges": sorted(self.bridges),
            "actions": {a: self.entry(a) for a in self.actions()},
        }

    def save(self, path: Path) -> None:
        """Write the table as JSON, one action per line, via a temporary file."""
        data = self.to_json()
        head = {k: v for k, v in data.items() if k != "actions"}
        lines = ["{"] + [f"  {json.dumps(k)}: {json.dumps(v)}," for k, v in head.items()]
        entries = [f"    {json.dumps(a)}: {json.dumps(e)}" for a, e in data["actions"].items()]
        lines += ['  "actions": {', ",\n".join(entries), "  }", "}"] if entries else ['  "actions": {}', "}"]
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_name(path.name + ".tmp")
        tmp.write_text("\n".join(line for line in lines if line) + "\n", encoding="utf-8")
        tmp.replace(path)

    @classmethod
    def load(cls, path: Path) -> "CostTable":
        try:
            data = json.loads(Path(path).read_text(encoding="utf-8"))
        except (OSError, ValueError) as e:
            raise CostingError(f"cannot read cost table {path}: {e}") from e
        if not isinstance(data, dict) or data.get("version") != TABLE_VERSION:
            raise CostingError(f"{path} is not a version {TABLE_VERSION} cost table")
        table = cls()
        table.skips = data.get("skips")
        table.engine = data.get("engine")
        table.bridges = set(data.get("bridges") or [])
        for action, entry in (data.get("actions") or {}).items():
            samples = entry.get("samples") if isinstance(entry, dict) else None
            if not isinstance(samples, list) or not all(isinstance(s, int) for s in samples):
                raise CostingError(f"{path}: action {action!r} has no integer 'samples' list")
            table._samples[action] = list(samples)
        return table
