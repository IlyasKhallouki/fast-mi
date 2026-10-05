"""Validate extracted PDDL fragments and their script citations (Phase 7).

Extraction subagents read the descumm dump (``data/scripts``) and write
fragment files ``out/extract/<segment>/<group>.pddl``. A fragment holds
nothing but ground ``(:action ...)`` blocks. Each block starts on its own line
and is *immediately* preceded (no blank line) by a block of comment lines:

- ``; src: data/scripts/<file> [XXXX] — <text>``: one or more, required.
  ``<file>`` exists under ``data/scripts`` and ``[XXXX]`` (four upper-case hex
  digits) occurs in it.
- exactly one player-input line, required:
  - ``; sentence: <verb> <objA> [<objB>]``
  - ``; click: <verb>,inv:<obj>[,<offset>]``

  The verb is one of ``VERBS`` (2..11). The click clicks the verb slot, then the
  inventory slot showing ``<obj>``, shifted by the non-zero ``<offset>`` (C4).
- ``; room: <N>``: exactly one, required. ``N`` is the engine room; in the forest
  it is the pseudo-room 201-220.
- ``; dialogue: <ASCII substring>``: optional, repeatable; the menu choices to
  pick during the action, in order (C4 ``choose``).

A comment line with a single ``;`` must be one of these annotations, so a typo
cannot pass as a comment. Free comments start with ``;;``.

Atoms are 0-ary and name engine state, so fragments merge mechanically
(``parse_atom``): ``at-rN``, ``has-oN``, ``bit-N``, ``state-oN-S`` (S 0..15),
``owner-oN-A`` (A 0..15), ``class-oN-C`` (C 1..32), ``var-N-eq-V`` and
``var-N-ge-V`` (V may be negative: ``var-54-eq--80``). Numbers have no leading
zeros. A precondition is a conjunction of atoms and ``(not atom)``. An effect is a
conjunction of literals plus exactly one ``(increase (total-cost) 1)``. Nothing
else is allowed (no parameters, ``when``, ``or``, quantifiers): the merged model
must stay inside the ``astar(lmcut())`` subset. A positive ``(at-rN)``
precondition must agree with ``; room:``.

``check_fragment`` lists the issues; ``filter_fragment`` drops every action
that has one and keeps the rest verbatim. Action names (case-insensitive) must
be unique across all fragments; every copy of a duplicate is rejected, so the
result does not depend on the order fragments are read in.

``citations_only=True`` applies only the ``; src:`` rules, to any PDDL file
(e.g. the hand-written ``pddl/part1/domain.pddl``, whose predicates are abstract).
"""

import re
from bisect import bisect_right
from collections import Counter
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import NamedTuple

VERBS = {
    2: "Open",
    3: "Close",
    4: "Give",
    5: "Push",
    6: "Pull",
    7: "Use",
    8: "Look at",
    9: "Pick up",
    10: "Talk to",
    11: "Walk to",
}
FOREST_ROOMS = range(201, 221)
REQUIREMENTS = (":strips", ":negative-preconditions", ":action-costs")
FRAGMENT = "<fragment>"  # the rejected-list name for problems that belong to no action

SRC_RE = re.compile(r"^; src: data/scripts/(?P<file>\S+) \[(?P<offset>[0-9A-F]{4})\] — (?P<text>\S.*)$")
_SENTENCE_RE = re.compile(r"^; sentence: (\d+) (\d+)(?: (\d+))?$")
_CLICK_RE = re.compile(r"^; click: (\d+),inv:(\d+)(?:,([+-]?\d+))?$")
_ROOM_RE = re.compile(r"^; room: (\d+)$")
_DIALOGUE_RE = re.compile(r"^; dialogue: (\S(?:.*\S)?)$")
_KEY_RE = re.compile(r"^;\s*([A-Za-z_-]+)\s*:")
ACTION_LINE_RE = re.compile(r"^\s*\(:action\s+([^\s()]+)", re.IGNORECASE)
_TOKEN_RE = re.compile(r";[^\n]*|\(|\)|[^\s();]+")

_NUM = r"(0|[1-9]\d*)"
_SIGNED = r"(0|-?[1-9]\d*)"
_ATOM_RES = (
    ("at", re.compile(rf"at-r{_NUM}")),
    ("has", re.compile(rf"has-o{_NUM}")),
    ("bit", re.compile(rf"bit-{_NUM}")),
    ("state", re.compile(rf"state-o{_NUM}-{_NUM}")),
    ("owner", re.compile(rf"owner-o{_NUM}-{_NUM}")),
    ("class", re.compile(rf"class-o{_NUM}-{_NUM}")),
    ("var-eq", re.compile(rf"var-{_NUM}-eq-{_SIGNED}")),
    ("var-ge", re.compile(rf"var-{_NUM}-ge-{_SIGNED}")),
)
ATOM_KINDS = tuple(kind for kind, _ in _ATOM_RES)
_SECOND_ARG_RANGE = {"state": (0, 15), "owner": (0, 15), "class": (1, 32)}
_UNSUPPORTED = {"when", "forall", "exists", "or", "imply", "either", "=", ":derived"}
_VOCABULARY = "at-rN, has-oN, bit-N, state-oN-S, owner-oN-A, class-oN-C, var-N-eq-V, var-N-ge-V"


@dataclass(frozen=True)
class Issue:
    code: str
    message: str
    action: str | None = None  # None: the problem belongs to the fragment, not to one action
    line: int | None = None  # 1-based line in the fragment
    source: str | None = None  # the fragment's file name or label

    def __str__(self) -> str:
        where = f"{self.source or FRAGMENT}:{self.line or 0}"
        who = f" {self.action}:" if self.action else ""
        return f"{where}:{who} {self.message} [{self.code}]"


class CitationProblem(NamedTuple):
    code: str  # "missing-file" or "bad-offset"
    message: str

    def __str__(self) -> str:
        return self.message


class Atom(NamedTuple):
    kind: str  # one of ATOM_KINDS
    args: tuple[int, ...]


@dataclass(frozen=True)
class Citation:
    file: str  # relative to data/scripts
    offset: str  # four hex digits
    text: str
    line: int


@dataclass(frozen=True)
class Sentence:
    verb: int
    obj: int
    obj2: int = 0  # 0 = none


@dataclass(frozen=True)
class Click:
    verb: int
    inventory: int
    offset: int = 0  # 0 = none


@dataclass
class Action:
    """One parsed fragment action, with the issues found in its own text."""

    name: str
    line: int
    text: str  # its comment block and the (:action ...) form, verbatim
    cites: list[Citation] = field(default_factory=list)
    inputs: list[Sentence | Click] = field(default_factory=list)
    rooms: list[int] = field(default_factory=list)
    dialogue: list[str] = field(default_factory=list)
    pre: list[tuple[bool, str]] = field(default_factory=list)  # (positive, atom name)
    eff: list[tuple[bool, str]] = field(default_factory=list)  # without the cost term
    issues: list[Issue] = field(default_factory=list)

    @property
    def input(self) -> Sentence | Click | None:
        return self.inputs[0] if len(self.inputs) == 1 else None

    @property
    def room(self) -> int | None:
        return self.rooms[0] if len(self.rooms) == 1 else None


@dataclass
class Fragment:
    actions: list[Action]
    issues: list[Issue]  # problems outside any action (parse errors, stray forms)


def parse_atom(name: str) -> Atom | None:
    """The vocabulary atom ``name`` names, or None if it is not one."""
    for kind, regex in _ATOM_RES:
        m = regex.fullmatch(name)
        if m:
            args = tuple(int(g) for g in m.groups())
            bounds = _SECOND_ARG_RANGE.get(kind)
            if bounds and not bounds[0] <= args[1] <= bounds[1]:
                return None
            return Atom(kind, args)
    return None


def citation_problem(
    scripts_dir: Path, rel: str, offset: str, cache: dict[Path, str] | None = None
) -> CitationProblem | None:
    """Why ``data/scripts/<rel> [<offset>]`` is not a valid citation under ``scripts_dir``, or None.

    The file must exist under ``scripts_dir`` and ``[<offset>]`` must occur in its text.
    ``cache`` maps already-read files to their text.
    """
    root = Path(scripts_dir)
    path = root / rel
    try:
        path.resolve().relative_to(root.resolve())
    except ValueError:
        return CitationProblem("missing-file", f"cited file {rel} lies outside {root}")
    if not path.is_file():
        return CitationProblem("missing-file", f"cited file {rel} does not exist")
    if cache is not None and path in cache:
        text = cache[path]
    else:
        text = path.read_text(encoding="utf-8", errors="replace")
        if cache is not None:
            cache[path] = text
    if f"[{offset}]" not in text:
        return CitationProblem("bad-offset", f"offset [{offset}] does not occur in {rel}")
    return None


# --- s-expressions --------------------------------------------------------------------


class SexpError(ValueError):
    def __init__(self, message: str, line: int):
        super().__init__(message)
        self.line = line


@dataclass
class _Form:
    items: list  # nested lists of lower-cased tokens
    start: int  # offset of "("
    end: int  # offset just past ")"
    line: int


def _line_of(starts: list[int], pos: int) -> int:
    return bisect_right(starts, pos)


def _line_starts(text: str) -> list[int]:
    return [0] + [m.end() for m in re.finditer("\n", text)]


def _top_level(text: str) -> tuple[list[_Form], list[tuple[str, int]]]:
    """Top-level forms and stray top-level tokens (with their lines); comments are skipped."""
    starts = _line_starts(text)
    forms: list[_Form] = []
    stray: list[tuple[str, int]] = []
    stack: list[tuple[list, int]] = []
    for m in _TOKEN_RE.finditer(text):
        tok = m.group()
        if tok.startswith(";"):
            continue
        if tok == "(":
            stack.append(([], m.start()))
        elif tok == ")":
            if not stack:
                raise SexpError("unmatched ')'", _line_of(starts, m.start()))
            items, start = stack.pop()
            if stack:
                stack[-1][0].append(items)
            else:
                forms.append(_Form(items, start, m.end(), _line_of(starts, start)))
        elif stack:
            stack[-1][0].append(tok.lower())
        else:
            stray.append((tok, _line_of(starts, m.start())))
    if stack:
        raise SexpError("unclosed '('", _line_of(starts, stack[-1][1]))
    return forms, stray


def parse_sexp(text: str) -> list:
    """Every top-level form of ``text`` as nested lists of lower-cased tokens (comments dropped)."""
    forms, stray = _top_level(text)
    if stray:
        raise SexpError(f"stray token {stray[0][0]!r}", stray[0][1])
    return [f.items for f in forms]


def render(expr) -> str:
    """An s-expression back as text."""
    if isinstance(expr, list):
        return "(" + " ".join(render(e) for e in expr) + ")"
    return expr


# --- annotation blocks --------------------------------------------------------------


def _comment_block(lines: list[str], index: int) -> list[tuple[int, str]]:
    """The comment lines directly above ``lines[index]``, top to bottom, as (1-based line, stripped text)."""
    block = []
    j = index - 1
    while j >= 0 and lines[j].strip().startswith(";"):
        block.append((j + 1, lines[j].strip()))
        j -= 1
    return block[::-1]


def _parse_annotations(act: Action, block: list[tuple[int, str]], issue) -> None:
    for lineno, line in block:
        if line.startswith(";;"):
            continue
        key_match = _KEY_RE.match(line)
        key = key_match.group(1).lower() if key_match else None
        if key == "src":
            m = SRC_RE.match(line)
            if m:
                act.cites.append(Citation(m["file"], m["offset"], m["text"], lineno))
            else:
                issue("bad-src", f"malformed citation {line!r}; write '; src: data/scripts/<file> [XXXX] — <text>' "
                      "(four upper-case hex digits)", lineno)  # fmt: skip
        elif key == "sentence":
            m = _SENTENCE_RE.match(line)
            verb, obj, obj2 = (int(g) if g else 0 for g in m.groups()) if m else (0, 0, 0)
            if not m or verb not in VERBS or obj <= 0 or (m.group(3) is not None and obj2 <= 0):
                issue("bad-sentence", f"malformed {line!r}; write '; sentence: <verb> <objA> [<objB>]' with a verb "
                      f"in {sorted(VERBS)} and object ids > 0", lineno)  # fmt: skip
            act.inputs.append(Sentence(verb, obj, obj2))
        elif key == "click":
            m = _CLICK_RE.match(line)
            verb, obj, offset = (int(g) if g else 0 for g in m.groups()) if m else (0, 0, 0)
            if not m or verb not in VERBS or obj <= 0 or (m.group(3) is not None and offset == 0):
                issue("bad-click", f"malformed {line!r}; write '; click: <verb>,inv:<obj>[,<non-zero offset>]' "
                      f"with a verb in {sorted(VERBS)}", lineno)  # fmt: skip
            act.inputs.append(Click(verb, obj, offset))
        elif key == "room":
            m = _ROOM_RE.match(line)
            if m:
                act.rooms.append(int(m.group(1)))
            else:
                issue("bad-room", f"malformed {line!r}; write '; room: <engine room number>'", lineno)
        elif key == "dialogue":
            m = _DIALOGUE_RE.match(line)
            if m and m.group(1).isascii():
                act.dialogue.append(m.group(1))
            else:
                issue("bad-dialogue", f"malformed {line!r}; write '; dialogue: <non-empty ASCII substring>' "
                      "(the bridge matches raw game bytes, docs/plan.md C5)", lineno)  # fmt: skip
        else:
            issue("bad-annotation", f"{line!r} is not an annotation (src, sentence, click, room, dialogue); "
                  "free comments start with ';;'", lineno)  # fmt: skip


# --- action bodies ----------------------------------------------------------------------


def _conjuncts(expr) -> list:
    if isinstance(expr, list) and expr and expr[0] == "and":
        return expr[1:]
    if expr == []:
        return []
    return [expr]


def _literal(expr, where: str, issue) -> tuple[bool, str] | None:
    """(positive, atom name) for ``(atom)`` or ``(not (atom))``; reports anything else."""
    positive = True
    if isinstance(expr, list) and len(expr) == 2 and expr[0] == "not":
        positive, expr = False, expr[1]
    if not isinstance(expr, list) or not expr:
        issue("bad-structure", f"{where}: expected an atom or (not atom), got {render(expr)}")
        return None
    head = expr[0]
    if isinstance(head, list):
        issue("bad-structure", f"{where}: expected an atom or (not atom), got {render(expr)}")
        return None
    if head in _UNSUPPORTED:
        issue("unsupported", f"{where}: {render(expr)} uses '{head}', which the lmcut-safe subset does not allow")
        return None
    if head in ("and", "not", "increase"):
        issue("bad-structure", f"{where}: expected an atom or (not atom), got {render(expr)}")
        return None
    if len(expr) > 1:
        issue("unknown-atom", f"{where}: {render(expr)} has arguments; atoms are 0-ary ({_VOCABULARY})")
        return None
    if parse_atom(head) is None:
        issue("unknown-atom", f"{where}: ({head}) is not in the vocabulary ({_VOCABULARY}; no leading zeros)")
        return None
    return positive, head


def _parse_body(act: Action, form: list, issue) -> None:
    body = form[2:]
    if len(body) % 2:
        issue("bad-structure", "expected ':keyword value' pairs after the action name")
        return
    keys = [str(k) for k in body[::2]]
    repeated = sorted({k for k in keys if keys.count(k) > 1})
    if repeated:
        issue("bad-structure", f"keyword(s) {repeated} given more than once")
    parts = dict(zip(body[::2], body[1::2], strict=True))
    unknown = sorted(str(k) for k in parts if k not in (":parameters", ":precondition", ":effect"))
    if unknown:
        issue("bad-structure", f"unknown keyword(s) {unknown}; allowed: :parameters, :precondition, :effect")
    if parts.get(":parameters", []) != []:
        issue("parameters", f":parameters {render(parts[':parameters'])}: fragment actions are ground (0-ary)")
    for conjunct in _conjuncts(parts.get(":precondition", [])):
        lit = _literal(conjunct, ":precondition", issue)
        if lit:
            act.pre.append(lit)
    if ":effect" not in parts:
        issue("no-cost", "no :effect, so no (increase (total-cost) 1)")
        return
    costs = []
    for conjunct in _conjuncts(parts[":effect"]):
        if isinstance(conjunct, list) and conjunct and conjunct[0] == "increase":
            costs.append(conjunct)
            continue
        lit = _literal(conjunct, ":effect", issue)
        if lit:
            act.eff.append(lit)
    if not costs:
        issue("no-cost", "the effect lacks (increase (total-cost) 1)")
    elif costs != [["increase", ["total-cost"], "1"]]:
        issue("bad-cost", f"the effect must cost exactly (increase (total-cost) 1), got {' '.join(map(render, costs))}")


def _check_annotations(act: Action, issue) -> None:
    if not act.cites and not any(i.code == "bad-src" for i in act.issues):
        issue("no-src", "no '; src: data/scripts/<file> [XXXX] — <text>' line in the comment block directly "
              "above '(:action' (no blank line in between)")  # fmt: skip
    if not act.inputs:
        issue("no-input", "no player-input line ('; sentence: ...' or '; click: ...')")
    elif len(act.inputs) > 1:
        issue("multiple-inputs", f"{len(act.inputs)} player-input lines; an action is exactly one sentence or click")
    if not act.rooms:
        if not any(i.code == "bad-room" for i in act.issues):
            issue("no-room", "no '; room: <engine room number>' line")
    elif len(act.rooms) > 1:
        issue("multiple-rooms", f"{len(act.rooms)} '; room:' lines; give exactly one")
    at_rooms = [parse_atom(name).args[0] for pos, name in act.pre if pos and name.startswith("at-r")]
    if len(at_rooms) > 1:
        issue("room-mismatch", f"preconditions put ego in {len(at_rooms)} rooms at once: {at_rooms}")
    elif at_rooms and act.room is not None and at_rooms[0] != act.room:
        issue("room-mismatch", f"'; room: {act.room}' but the precondition is (at-r{at_rooms[0]})")


def parse_fragment(text: str, source: str | None = None) -> Fragment:
    """Split a fragment into actions and check each one's own text (not the cited files, not names)."""
    try:
        forms, stray = _top_level(text)
    except SexpError as e:
        return Fragment([], [Issue("parse", f"{e}; nothing in this fragment can be read", None, e.line, source)])
    lines = text.splitlines()
    starts = _line_starts(text)
    issues = [
        Issue("not-action", f"stray token {tok!r} outside any (:action ...)", None, line, source)
        for tok, line in stray
    ]
    actions = []
    for form in forms:
        items = form.items
        if len(items) < 2 or items[0] != ":action" or not isinstance(items[1], str):
            head = render(items[:2]) if items else "()"
            issues.append(Issue("not-action", f"top-level form {head[:60]} is not an (:action <name> ...); "
                                "fragments hold only actions", None, form.line, source))  # fmt: skip
            continue
        line_start = starts[form.line - 1]
        at_line_start = not text[line_start : form.start].strip()
        block = _comment_block(lines, form.line - 1) if at_line_start else []
        begin = starts[block[0][0] - 1] if block else (line_start if at_line_start else form.start)
        act = Action(name=items[1], line=form.line, text=text[begin : form.end])

        def issue(code, message, line=None, _act=act):
            _act.issues.append(Issue(code, message, _act.name, line or _act.line, source))

        if not at_line_start:
            issue("layout", "'(:action' must start its own line, below its comment block")
        _parse_annotations(act, block, issue)
        _parse_body(act, items, issue)
        _check_annotations(act, issue)
        actions.append(act)
    return Fragment(actions, issues)


# --- checks over one fragment or many ---------------------------------------------------


def _citation_issues(act: Action, scripts_dir: Path, cache: dict, source: str | None) -> list[Issue]:
    out = []
    for c in act.cites:
        problem = citation_problem(scripts_dir, c.file, c.offset, cache)
        if problem:
            out.append(Issue(problem.code, problem.message, act.name, c.line, source))
    return out


def _duplicate_issue(name: str, line: int, source: str | None, elsewhere: list[str], twice: bool) -> Issue:
    where = []
    if twice:
        where.append("more than once in this fragment")
    if elsewhere:
        where.append("in " + ", ".join(elsewhere))
    return Issue("duplicate-name", f"action name {name!r} is also defined {' and '.join(where)}; names must be "
                 "unique across all fragments (every copy is rejected)", name, line, source)  # fmt: skip


def _defined(names_by_source: Mapping[str, list[str]]) -> dict[str, list[str]]:
    """name -> every source that defines it (once per definition)."""
    out: dict[str, list[str]] = {}
    for src, names in names_by_source.items():
        for name in names:
            out.setdefault(name, []).append(src)
    return out


def _elsewhere(defined: Mapping[str, list[str]], name: str, src: str, external: Mapping[str, str] | None) -> list[str]:
    out = sorted({s for s in defined.get(name, []) if s != src})
    if external and name in external:
        out.append(external[name])
    return out


def _checked(
    fragments: Mapping[str, str], scripts_dir: Path | None, external: Mapping[str, str] | None = None
) -> dict[str, tuple[Fragment, list[list[Issue]]]]:
    """Parse every fragment; each action's issues (its own, its citations', its name's), by position."""
    cache: dict[Path, str] = {}
    parsed = {src: parse_fragment(text, src) for src, text in fragments.items()}
    defined = _defined({src: [a.name for a in frag.actions] for src, frag in parsed.items()})
    out = {}
    for src, frag in parsed.items():
        per_action = []
        for act in frag.actions:
            issues = list(act.issues)
            if scripts_dir is not None:
                issues += _citation_issues(act, scripts_dir, cache, src)
            elsewhere = _elsewhere(defined, act.name, src, external)
            twice = defined[act.name].count(src) > 1
            if elsewhere or twice:
                issues.append(_duplicate_issue(act.name, act.line, src, elsewhere, twice))
            per_action.append(issues)
        out[src] = (frag, per_action)
    return out


def _flatten(checked) -> list[Issue]:
    issues = []
    for frag, per_action in checked.values():
        issues += frag.issues
        for action_issues in per_action:
            issues += action_issues
    return issues


def _strip_source(issues: list[Issue], source: str | None) -> list[Issue]:
    return [Issue(i.code, i.message, i.action, i.line, source) for i in issues]


_SINGLE = "\0fragment"


def _label(source: str | None) -> str:
    return source if source is not None else _SINGLE


def check_fragment(
    text: str,
    scripts_dir: Path | None,
    *,
    other_names: Mapping[str, str] | Iterable[str] = (),
    source: str | None = None,
    citations_only: bool = False,
) -> list[Issue]:
    """Every issue in one fragment.

    ``scripts_dir`` None skips the file and offset checks. ``other_names`` are
    action names defined elsewhere (a mapping gives where), which this fragment
    must not reuse.
    """
    others = other_names if isinstance(other_names, Mapping) else {n: "another fragment" for n in other_names}
    if citations_only:
        return _citations_only(text, scripts_dir, source, others)
    issues = _flatten(_checked({_label(source): text}, scripts_dir, others))
    return _strip_source(issues, source)


def check_fragments(
    fragments: Mapping[str, str], scripts_dir: Path | None, *, citations_only: bool = False
) -> list[Issue]:
    """Every issue in ``{source: text}``, names checked for uniqueness across all of them."""
    if not citations_only:
        return _flatten(_checked(fragments, scripts_dir))
    defined = _defined({src: [name for name, _ in _action_lines(text)] for src, text in fragments.items()})
    issues = []
    for src, text in fragments.items():
        external = {name: ", ".join(where) for name in defined if (where := _elsewhere(defined, name, src, None))}
        issues += _citations_only(text, scripts_dir, src, external)
    return issues


def filter_fragment(
    text: str,
    scripts_dir: Path | None,
    *,
    other_names: Mapping[str, str] | Iterable[str] = (),
    source: str | None = None,
) -> tuple[str, list[tuple[str, list[Issue]]]]:
    """``(accepted text, [(action, issues)])``: every action with an issue is dropped, the rest kept verbatim.

    A fragment that cannot be parsed keeps nothing and is rejected as one ``FRAGMENT`` entry.
    Problems outside any action (stray forms) are reported as a ``FRAGMENT`` entry, and
    the actions are still kept.
    """
    others = other_names if isinstance(other_names, Mapping) else {n: "another fragment" for n in other_names}
    checked = _checked({_label(source): text}, scripts_dir, others)
    accepted, rejected = _split(checked)
    return accepted[_label(source)], [(name, _strip_source(issues, source)) for _, name, issues in rejected]


def filter_fragments(
    fragments: Mapping[str, str], scripts_dir: Path | None
) -> tuple[dict[str, str], list[tuple[str, str, list[Issue]]]]:
    """``({source: accepted text}, [(source, action, issues)])`` over many fragments."""
    return _split(_checked(fragments, scripts_dir))


def _split(checked) -> tuple[dict[str, str], list[tuple[str, str, list[Issue]]]]:
    accepted: dict[str, str] = {}
    rejected: list[tuple[str, str, list[Issue]]] = []
    for src, (frag, per_action) in checked.items():
        if frag.issues:
            rejected.append((src, FRAGMENT, frag.issues))
        kept = []
        for act, issues in zip(frag.actions, per_action, strict=True):
            if issues:
                rejected.append((src, act.name, issues))
            else:
                kept.append(act.text)
        accepted[src] = "\n\n".join(kept) + ("\n" if kept else "")
    return accepted, rejected


# --- citations only ----------------------------------------------------------------------


def _action_lines(text: str) -> list[tuple[str, int]]:
    """(lower-cased name, 0-based line index) of every line that opens an action."""
    out = []
    for i, line in enumerate(text.splitlines()):
        m = ACTION_LINE_RE.match(line)
        if m:
            out.append((m.group(1).lower(), i))
    return out


def action_names(text: str) -> list[str]:
    """The lower-cased name of every line of ``text`` that opens an ``(:action``."""
    return [name for name, _ in _action_lines(text)]


def action_citations(text: str) -> dict[str, list[Citation]]:
    """The ``; src:`` citations directly above each action of any PDDL file (malformed lines skipped)."""
    lines = text.splitlines()
    out: dict[str, list[Citation]] = {}
    for name, i in _action_lines(text):
        cites = out.setdefault(name, [])
        for lineno, line in _comment_block(lines, i):
            m = SRC_RE.match(line)
            if m:
                cites.append(Citation(m["file"], m["offset"], m["text"], lineno))
    return out


def _citations_only(
    text: str, scripts_dir: Path | None, source: str | None, external: Mapping[str, str]
) -> list[Issue]:
    lines = text.splitlines()
    entries = _action_lines(text)
    counts = Counter(name for name, _ in entries)
    cache: dict[Path, str] = {}
    issues: list[Issue] = []
    for name, i in entries:
        act = Action(name=name, line=i + 1, text="")
        malformed = False
        for lineno, line in _comment_block(lines, i):
            key = _KEY_RE.match(line)
            if line.startswith(";;") or not key or key.group(1).lower() != "src":
                continue
            m = SRC_RE.match(line)
            if m:
                act.cites.append(Citation(m["file"], m["offset"], m["text"], lineno))
            else:
                malformed = True
                issues.append(Issue("bad-src", f"malformed citation {line!r}; write '; src: data/scripts/<file> "
                                    "[XXXX] — <text>'", name, lineno, source))  # fmt: skip
        if not act.cites and not malformed:
            issues.append(Issue("no-src", "no '; src:' line in the comment block directly above '(:action'",
                                name, i + 1, source))  # fmt: skip
        if scripts_dir is not None:
            issues += _citation_issues(act, scripts_dir, cache, source)
        elsewhere = [external[name]] if name in external else []
        if counts[name] > 1 or elsewhere:
            issues.append(_duplicate_issue(name, i + 1, source, elsewhere, counts[name] > 1))
    return issues
