"""Compare the hand-written model with the extracted one (Phase 7, ``speedrun pddl-diff``).

The two models share no predicates (the hand model's are abstract, the
extracted ones name engine state), so actions are matched by what the player
does: the *signature* of an action is its sentence ``(verb, obj, obj2)`` or its
click ``(verb, inventory, offset)``, plus the room it is given in.

- Hand model: each ground action's ``steps.toml`` template is compiled with the
  compiler's ``ObjectIndex``. Its main step is the last step with a sentence or
  click. The room is the step's ``room``, or for forest steps the VAR_ROOM
  ``until`` value; a step with neither (an inventory sentence) matches any room.
- Extracted model: the ``; sentence:``/``; click:`` and ``; room:`` annotations.

Several actions can share a signature (split pairs, the circus helmet
variants), so a match is a group on each side. For each match the report shows
the citation overlap, both sides' preconditions and effects, and their counts.
It also compares room-to-room links: ``at-rN`` changes in the extracted model,
and the hand model's ``(at ...)`` changes with each node mapped to the room its
templates are given in.
"""

import json
import re
from collections import Counter
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from pathlib import Path

from speedrun.citations import VERBS, Action, Click, action_citations, parse_atom, parse_sexp, render
from speedrun.compiler import CompileError, ObjectIndex, compile_plan
from speedrun.extract import VAR_ROOM, sourced_actions
from speedrun.planner import Plan

_LINK_CITE_RE = re.compile(r"; src: data/scripts/(\S+) \[([0-9A-F]{4})\]")
_FACT_RE = re.compile(r"\(\s*([^\s()]+)((?:\s+[^\s()]+)*)\s*\)")


@dataclass(frozen=True)
class Signature:
    """Player input. For a click, ``obj`` is the inventory object and ``obj2`` the slot offset."""

    kind: str  # "sentence" or "click"
    verb: int
    obj: int
    obj2: int
    room: int | None  # None: any room (hand inventory sentences)

    def core(self) -> tuple:
        return self.kind, self.verb, self.obj, self.obj2

    def accepts(self, other: "Signature") -> bool:
        """This (hand) signature matches ``other`` (extracted)."""
        return self.core() == other.core() and (self.room is None or self.room == other.room)

    def sort_key(self) -> tuple:
        return self.room if self.room is not None else -1, self.kind, self.verb, self.obj, self.obj2

    def label(self) -> str:
        verb = VERBS.get(self.verb, f"verb {self.verb}")
        where = f"in room {self.room}" if self.room is not None else "(any room)"
        if self.kind == "click":
            offset = f" (offset {self.obj2})" if self.obj2 else ""
            return f"click {verb} + inventory {self.obj}{offset} {where}"
        objects = f"{self.obj} {self.obj2}" if self.obj2 else f"{self.obj}"
        return f"{verb} {objects} {where}"


@dataclass
class ActionSummary:
    name: str
    pre: list[str]
    eff: list[str]
    cites: list[tuple[str, str]]  # (file under data/scripts, offset)
    counts: tuple[int, int, int, int]  # (pre +, pre -, add, delete)


@dataclass
class Match:
    signature: Signature  # the hand side's
    hand: list[ActionSummary]
    extracted: list[ActionSummary]
    cited_by_both: list[tuple[str, str]]
    cited_by_hand_only: list[tuple[str, str]]
    cited_by_extracted_only: list[tuple[str, str]]


@dataclass
class Transition:
    source: int | None  # None: the extracted action moves ego without an (at-rN) precondition
    target: int
    hand: list[str] = field(default_factory=list)
    extracted: list[str] = field(default_factory=list)


@dataclass
class Report:
    matched: list[Match]
    hand_only: list[tuple[Signature, list[str]]]
    extracted_only: list[tuple[Signature, list[str]]]
    hand_unsigned: list[tuple[str, str]]  # (hand action, why it has no signature)
    transitions: list[Transition]
    unmapped_links: list[tuple[str, str, str]]  # (hand action, from node, to node) with a node of unknown room
    intra_room_links: list[tuple[str, str, str, int]]  # (hand action, from node, to node, room)
    hand_count: int
    extracted_count: int

    def to_markdown(self, title: str = "Extraction diff", notes: Iterable[str] = ()) -> str:
        return _markdown(self, title, list(notes))


# --- signatures ----------------------------------------------------------------------------


def step_signature(step: Mapping) -> Signature | None:
    """The signature of a compiled C4 step, or None for a dialogue-only step."""
    room = step.get("room")
    if room is None:
        room = next((c["eq"] for c in step.get("until", []) if c.get("var") == VAR_ROOM and "eq" in c), None)
    if "verb" in step:
        return Signature("sentence", step["verb"], step["obj"], step.get("obj2", 0), room)
    if "click" in step:
        verb = next((c["verb"] for c in step["click"] if "verb" in c), 0)
        slot = next((c for c in step["click"] if "inventory" in c), {})
        return Signature("click", verb, slot.get("inventory", 0), slot.get("offset", 0), room)
    return None


def extracted_signature(act: Action) -> Signature:
    inp = act.input
    if isinstance(inp, Click):
        return Signature("click", inp.verb, inp.inventory, inp.offset, act.room)
    return Signature("sentence", inp.verb, inp.obj, inp.obj2, act.room)


def _hand_signature(key: str, steps: Mapping, objects: ObjectIndex) -> Signature | str:
    try:
        compiled = compile_plan(Plan(actions=[tuple(key.split())], cost=1), steps, objects)
    except CompileError as e:
        return f"template does not compile: {e}"
    for step in reversed(compiled):
        sig = step_signature(step)
        if sig is not None:
            return sig
    return "no sentence or click step (dialogue only)"


# --- the hand model ------------------------------------------------------------------------


@dataclass
class _HandAction:
    name: str  # the ground action, as a steps.toml key
    pre: list[tuple[bool, list]]
    eff: list[tuple[bool, list]]
    cites: list[tuple[str, str]]


def _flatten(expr) -> list[tuple[bool, list]]:
    if not isinstance(expr, list) or not expr:
        return []
    if expr[0] == "and":
        return [lit for sub in expr[1:] for lit in _flatten(sub)]
    if expr[0] == "not":
        return [(not pos, atom) for pos, atom in _flatten(expr[1])]
    if expr[0] == "increase":
        return []
    return [(True, expr)]


def _fact_cites(problem: str) -> dict[tuple[str, ...], list[tuple[str, str]]]:
    """Ground args of every cited fact line in the problem -> its citations."""
    out: dict[tuple[str, ...], list[tuple[str, str]]] = {}
    for line in problem.splitlines():
        code, _, comment = line.partition(";")
        cites = _LINK_CITE_RE.findall(";" + comment) if comment else []
        if not cites:
            continue
        for m in _FACT_RE.finditer(code):
            args = tuple(m.group(2).lower().split())
            if args:
                out.setdefault(args, []).extend(cites)
    return out


def _hand_actions(domain: str, problem: str, steps: Mapping) -> list[_HandAction]:
    (tree,) = [f for f in parse_sexp(domain) if f and f[0] == "define"]
    cites = action_citations(domain)
    fact_cites = _fact_cites(problem)
    keys = list((steps.get("actions") or {}).keys())
    out = []
    for item in tree:
        if not (isinstance(item, list) and item and item[0] == ":action"):
            continue
        name = item[1]
        parts = dict(zip(item[2::2], item[3::2], strict=False))
        params = [t for t in parts.get(":parameters", []) if isinstance(t, str) and t.startswith("?")]
        pre, eff = _flatten(parts.get(":precondition", [])), _flatten(parts.get(":effect", []))
        if not params:
            own = [(c.file, c.offset) for c in cites.get(name, [])]
            out.append(_HandAction(name, pre, eff, own))
            continue
        # A parameterised action (the generic walk) is compared per ground instance in steps.toml;
        # each instance carries the citations of the problem facts with its arguments (its link).
        for key in keys:
            words = key.split()
            if words[0] != name or len(words) != len(params) + 1:
                continue
            bind = dict(zip(params, words[1:], strict=True))

            def ground(lits, bind=bind):
                return [(pos, [bind.get(t, t) for t in atom]) for pos, atom in lits]

            out.append(_HandAction(key, ground(pre), ground(eff), fact_cites.get(tuple(words[1:]), [])))
    return out


# --- summaries --------------------------------------------------------------------------------


def _text(pos: bool, atom: str) -> str:
    return atom if pos else f"(not {atom})"


def _counts(pre: list[tuple[bool, object]], eff: list[tuple[bool, object]]) -> tuple[int, int, int, int]:
    return (
        sum(1 for pos, _ in pre if pos),
        sum(1 for pos, _ in pre if not pos),
        sum(1 for pos, _ in eff if pos),
        sum(1 for pos, _ in eff if not pos),
    )


def _hand_summary(act: _HandAction) -> ActionSummary:
    return ActionSummary(
        act.name,
        [_text(pos, render(atom)) for pos, atom in act.pre],
        [_text(pos, render(atom)) for pos, atom in act.eff],
        sorted(set(act.cites)),
        _counts(act.pre, act.eff),
    )


def _extracted_summary(act: Action) -> ActionSummary:
    return ActionSummary(
        act.name,
        [_text(pos, f"({atom})") for pos, atom in act.pre],
        [_text(pos, f"({atom})") for pos, atom in act.eff],
        sorted({(c.file, c.offset) for c in act.cites}),
        _counts(act.pre, act.eff),
    )


def _match(sig: Signature, hand: list[ActionSummary], extracted: list[ActionSummary]) -> Match:
    h = {c for a in hand for c in a.cites}
    e = {c for a in extracted for c in a.cites}
    return Match(sig, hand, extracted, sorted(h & e), sorted(h - e), sorted(e - h))


# --- transitions ------------------------------------------------------------------------------


def _node_rooms(hand: list[_HandAction], signatures: Mapping[str, Signature | str]) -> dict[str, int]:
    """Each hand room node -> the room its action templates are given in (the most common one)."""
    votes: dict[str, Counter] = {}
    for act in hand:
        sig = signatures[act.name]
        if not isinstance(sig, Signature) or sig.room is None:
            continue
        for pos, atom in act.pre:
            if pos and atom[0] == "at" and len(atom) == 2 and not atom[1].startswith("?"):
                votes.setdefault(atom[1], Counter())[sig.room] += 1
    return {node: min(c, key=lambda r: (-c[r], r)) for node, c in votes.items()}


def _moves(pre: Iterable[tuple[bool, object]], eff: Iterable[tuple[bool, object]], at) -> list[tuple]:
    sources = {at(a) for pos, a in pre if pos and at(a) is not None}
    targets = {at(a) for pos, a in eff if pos and at(a) is not None}
    return [(s, t) for t in sorted(targets, key=str) for s in sorted(sources, key=str) or [None] if s != t]


def _hand_at(atom) -> str | None:
    return atom[1] if atom[0] == "at" and len(atom) == 2 else None


def _extracted_at(atom: str) -> int | None:
    parsed = parse_atom(atom)
    return parsed.args[0] if parsed and parsed.kind == "at" else None


# --- diff -------------------------------------------------------------------------------------


def _read(value) -> str:
    return value.read_text(encoding="utf-8") if isinstance(value, Path) else value


def diff(
    hand_domain: str | Path,
    hand_problem: str | Path,
    hand_steps_toml: Mapping,
    objects_index: ObjectIndex,
    extracted_fragments: Mapping[str, str] | Iterable[str],
) -> Report:
    """Match the hand model's ground actions with the extracted actions by signature, and compare them."""
    hand = _hand_actions(_read(hand_domain), _read(hand_problem), hand_steps_toml)
    extracted = [act for _, act in sourced_actions(extracted_fragments)]

    signatures = {act.name: _hand_signature(act.name, hand_steps_toml, objects_index) for act in hand}
    hand_by_sig: dict[Signature, list[_HandAction]] = {}
    unsigned = []
    for act in hand:
        sig = signatures[act.name]
        if isinstance(sig, Signature):
            hand_by_sig.setdefault(sig, []).append(act)
        else:
            unsigned.append((act.name, sig))
    ext_by_sig: dict[Signature, list[Action]] = {}
    for act in extracted:
        ext_by_sig.setdefault(extracted_signature(act), []).append(act)

    matched, hand_only, used = [], [], set()
    for sig in sorted(hand_by_sig, key=Signature.sort_key):
        compatible = [e for e in sorted(ext_by_sig, key=Signature.sort_key) if sig.accepts(e)]
        names = [a.name for a in hand_by_sig[sig]]
        if not compatible:
            hand_only.append((sig, names))
            continue
        used.update(compatible)
        others = [_extracted_summary(a) for e in compatible for a in ext_by_sig[e]]
        matched.append(_match(sig, [_hand_summary(a) for a in hand_by_sig[sig]], others))
    extracted_only = [
        (sig, [a.name for a in ext_by_sig[sig]]) for sig in sorted(ext_by_sig, key=Signature.sort_key) if sig not in used
    ]

    rooms = _node_rooms(hand, signatures)
    links: dict[tuple, Transition] = {}
    unmapped, intra = [], []
    for act in hand:
        for a, b in _moves(act.pre, act.eff, _hand_at):
            ra, rb = rooms.get(a), rooms.get(b)
            if ra is None or rb is None:
                unmapped.append((act.name, a, b))
            elif ra == rb:
                intra.append((act.name, a, b, ra))
            else:
                links.setdefault((ra, rb), Transition(ra, rb)).hand.append(act.name)
    for act in extracted:
        for a, b in _moves(act.pre, act.eff, _extracted_at):
            links.setdefault((a, b), Transition(a, b)).extracted.append(act.name)
    transitions = [links[k] for k in sorted(links, key=lambda k: (k[0] if k[0] is not None else -1, k[1]))]

    return Report(
        matched=matched,
        hand_only=hand_only,
        extracted_only=extracted_only,
        hand_unsigned=unsigned,
        transitions=transitions,
        unmapped_links=unmapped,
        intra_room_links=intra,
        hand_count=len(hand),
        extracted_count=len(extracted),
    )


def index_from_script_dump(path: Path) -> ObjectIndex:
    """An ``ObjectIndex`` (C6 shape) built from the script dump's ``data/scripts/index.json``."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    rooms: dict[int, list[dict]] = {}
    for oid, obj in data["objects"].items():
        rooms.setdefault(int(obj["room"]), []).append({"id": int(oid), "name": obj["name"]})
    return ObjectIndex.from_dict(
        {
            "rooms": [{"room": r, "objects": objs} for r, objs in sorted(rooms.items())],
            "verbs": [{"id": int(v), "name": info["name"]} for v, info in data["verbs"].items()],
        }
    )


# --- Markdown ------------------------------------------------------------------------------------


def _names(names: Iterable[str]) -> str:
    return ", ".join(f"`{n}`" for n in names) or "none"


def _cites(cites: Iterable[tuple[str, str]]) -> str:
    return ", ".join(f"`{f} [{o}]`" for f, o in cites) or "none"


def _room(room: int | None) -> str:
    return "any" if room is None else str(room)


def _markdown(r: Report, title: str, notes: list[str]) -> str:
    both = [t for t in r.transitions if t.hand and t.extracted]
    hand_links = [t for t in r.transitions if t.hand and not t.extracted]
    ext_links = [t for t in r.transitions if t.extracted and not t.hand]
    out = [f"# {title}", ""]
    if notes:
        out += [*notes, ""]
    out += [
        (
            "`speedrun pddl-diff` writes this report. It matches actions by player input: the sentence (verb, "
            "objects) or click of an action's main step, plus the room that step is given in. A hand step without "
            "a room (an inventory sentence) matches any room. Object and verb ids come from the engine dump."
        ),
        "",
        "## Summary",
        "",
        "| | count |",
        "|---|---:|",
        f"| hand ground actions | {r.hand_count} |",
        f"| extracted actions | {r.extracted_count} |",
        f"| matched signatures | {len(r.matched)} |",
        f"| hand-only signatures | {len(r.hand_only)} |",
        f"| extracted-only signatures | {len(r.extracted_only)} |",
        f"| hand actions without a signature | {len(r.hand_unsigned)} |",
        f"| room links in both models | {len(both)} |",
        f"| room links only in the hand model | {len(hand_links)} |",
        f"| room links only in the extracted model | {len(ext_links)} |",
        "",
        "## Matched",
        "",
    ]
    if not r.matched:
        out += ["None.", ""]
    for m in r.matched:
        out += [
            f"### {m.signature.label()}",
            "",
            "| model | action | pre (+/−) | effect (add/del) |",
            "|---|---|---|---|",
        ]
        for model, acts in (("hand", m.hand), ("extracted", m.extracted)):
            for a in acts:
                p, n, add, dele = a.counts
                out.append(f"| {model} | `{a.name}` | {p}/{n} | {add}/{dele} |")
        out += [
            "",
            (
                f"Cited by both: {_cites(m.cited_by_both)}. Hand only: {_cites(m.cited_by_hand_only)}. "
                f"Extracted only: {_cites(m.cited_by_extracted_only)}."
            ),
            "",
            "```",
        ]
        for model, acts in (("hand", m.hand), ("extracted", m.extracted)):
            for a in acts:
                out += [f"{model} {a.name}", f"  pre: {' '.join(a.pre) or '—'}", f"  eff: {' '.join(a.eff) or '—'}"]
        out += ["```", ""]
    for heading, rows, who in (
        ("Hand-only", r.hand_only, "hand actions"),
        ("Extracted-only", r.extracted_only, "extracted actions"),
    ):
        out += [f"## {heading}", ""]
        if rows:
            out += [f"| signature | {who} |", "|---|---|"]
            out += [f"| {sig.label()} | {_names(names)} |" for sig, names in rows]
        else:
            out.append("None.")
        out.append("")
    out += ["## Hand actions without a signature", ""]
    if r.hand_unsigned:
        out += ["| action | why |", "|---|---|"]
        out += [f"| `{name}` | {why.replace('|', '/')} |" for name, why in r.hand_unsigned]
    else:
        out.append("None.")
    out += [
        "",
        "## Transitions",
        "",
        (
            "A room-to-room link is an `at-rN` change in the extracted model, or an `(at ...)` change in the hand "
            "model with each node mapped to the room its step templates are given in. A `from` of `any` marks an "
            "extracted action that moves ego without an `(at-rN)` precondition."
        ),
        "",
        "| from | to | hand | extracted |",
        "|---:|---:|---|---|",
    ]
    out += [f"| {_room(t.source)} | {t.target} | {_names(t.hand)} | {_names(t.extracted)} |" for t in r.transitions]
    out.append("")
    if r.unmapped_links:
        out.append("Hand links with a node whose room is unknown, because no step template is given there: "
                   + "; ".join(f"`{n}` ({a} → {b})" for n, a, b in r.unmapped_links) + ".")  # fmt: skip
        out.append("")
    if r.intra_room_links:
        out.append("Hand links inside one engine room, which the diff cannot compare because the extracted atoms "
                   "only see rooms: "
                   + "; ".join(f"`{n}` ({a} → {b}, room {room})" for n, a, b, room in r.intra_room_links) + ".")  # fmt: skip
        out.append("")
    return "\n".join(out)
