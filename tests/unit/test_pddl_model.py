"""Checks on the hand-written Part I planning model (``pddl/part1``).

The model is ``domain.pddl`` + ``problem.pddl`` (Fast Downward,
``astar(lmcut())``), ``steps.toml`` (C8: ground action -> plan steps) and
``segment.toml`` (C9). These tests are static: they parse the PDDL with a tiny
s-expression reader, check citations against ``data/scripts`` when the
script dump exists, and compile every ``steps.toml`` template against an
``ObjectIndex`` built from ``data/scripts/index.json``. The ``requires_fd``
test runs the real planner.

Model conventions the tests enforce (see ``docs/part1/model.md``):

- only the generic ``walk ?from ?to`` action has parameters; every other
  action is 0-ary, so its name is its only ground instance;
- an action changes ``(at ...)`` if and only if its name starts with ``walk``;
- every action costs exactly ``(increase (total-cost) 1)``.
"""

import json
import re
import tomllib

import pytest

from speedrun import paths
from speedrun.compiler import ObjectIndex, compile_plan
from speedrun.planner import Plan, run_planner
from speedrun.segments import load_segment

MODEL = paths.PDDL_DIR / "part1"
DOMAIN = MODEL / "domain.pddl"
PROBLEM = MODEL / "problem.pddl"
STEPS = MODEL / "steps.toml"
SCRIPTS = paths.DATA_DIR / "scripts"
INDEX = SCRIPTS / "index.json"

SRC_RE = re.compile(r"^\s*; src: data/scripts/(\S+) \[([0-9A-F]{4})\]")
ACTION_LINE_RE = re.compile(r"^\s*\(:action\s+(\S+)", re.IGNORECASE)
LINK_LINE_RE = re.compile(r"\(link\s+(\S+)\s+(\S+)\)")
ALLOWED_REQUIREMENTS = {":strips", ":typing", ":negative-preconditions", ":action-costs", ":equality"}
# Features astar(lmcut()) rejects or that compile to axioms (docs/research/fast-downward.md section 6).
FORBIDDEN_KEYWORDS = {"when", "forall", "exists", "or", "imply", ":derived", "either"}


# --- tiny PDDL reader ----------------------------------------------------------


def _strip_comments(text: str) -> str:
    return "\n".join(line.split(";", 1)[0] for line in text.splitlines())


def _parse_sexp(text: str):
    tokens = re.findall(r"\(|\)|[^\s()]+", _strip_comments(text).lower())
    stack: list[list] = [[]]
    for tok in tokens:
        if tok == "(":
            stack.append([])
        elif tok == ")":
            done = stack.pop()
            stack[-1].append(done)
        else:
            stack[-1].append(tok)
    assert len(stack) == 1, "unbalanced parentheses"
    (tree,) = stack[0]
    return tree


def _section(tree: list, key: str) -> list:
    for item in tree:
        if isinstance(item, list) and item and item[0] == key:
            return item
    raise AssertionError(f"no {key} section")


def _keyword_value(action: list, key: str):
    i = action.index(key)
    return action[i + 1]


def _atoms(expr) -> list[tuple[bool, list]]:
    """Flatten a precondition/effect into (positive, atom) pairs; skips the cost term."""
    if not isinstance(expr, list) or not expr:
        return []
    head = expr[0]
    if head == "and":
        return [a for sub in expr[1:] for a in _atoms(sub)]
    if head == "not":
        return [(False, atom) for _, atom in _atoms(expr[1])]
    if head == "increase":
        return []
    return [(True, expr)]


def _walk(expr):
    if isinstance(expr, list):
        yield expr
        for sub in expr:
            yield from _walk(sub)


def _domain_tree():
    return _parse_sexp(DOMAIN.read_text())


def _actions() -> dict[str, list]:
    tree = _domain_tree()
    out = {}
    for item in tree:
        if isinstance(item, list) and item and item[0] == ":action":
            name = item[1]
            assert name not in out, f"duplicate action {name}"
            out[name] = item
    return out


def _problem_links() -> list[tuple[str, str]]:
    init = _section(_parse_sexp(PROBLEM.read_text()), ":init")[1:]
    return [(f[1], f[2]) for f in init if f[0] == "link"]


def _steps() -> dict:
    with STEPS.open("rb") as f:
        return tomllib.load(f)


def _script_index() -> ObjectIndex:
    """An ObjectIndex in the C6 dump shape, built from the script dump's index.json."""
    data = json.loads(INDEX.read_text(encoding="utf-8"))
    rooms: dict[int, list[dict]] = {}
    for oid, obj in data["objects"].items():
        rooms.setdefault(int(obj["room"]), []).append({"id": int(oid), "name": obj["name"]})
    return ObjectIndex.from_dict(
        {
            "rooms": [{"room": r, "objects": objs} for r, objs in sorted(rooms.items())],
            "verbs": [{"id": int(v), "name": info["name"]} for v, info in data["verbs"].items()],
        }
    )


def _require_index() -> None:
    if not INDEX.is_file():
        pytest.skip(
            "SCRIPT DUMP MISSING: data/scripts/index.json not found — run scripts/dump-scripts.sh; "
            "steps.toml names were NOT checked against the game's object names"
        )


# --- citations ------------------------------------------------------------------


def _check_src_line(line: str, where: str) -> None:
    m = SRC_RE.match(line)
    assert m, f"{where}: malformed citation {line.strip()!r}"
    if SCRIPTS.is_dir():
        rel, offset = m.groups()
        path = SCRIPTS / rel
        assert path.is_file(), f"{where}: cited file {rel} does not exist"
        assert f"[{offset}]" in path.read_text(encoding="utf-8", errors="replace"), (
            f"{where}: offset [{offset}] does not occur in {rel}"
        )


def test_every_action_is_cited():
    lines = DOMAIN.read_text().splitlines()
    seen = 0
    for i, line in enumerate(lines):
        m = ACTION_LINE_RE.match(line)
        if not m:
            continue
        seen += 1
        name = m.group(1)
        cites = []
        j = i - 1
        while j >= 0 and lines[j].lstrip().startswith("; src:"):
            cites.append(lines[j])
            j -= 1
        assert cites, f"action {name} is not immediately preceded by a '; src:' line"
        for c in cites:
            _check_src_line(c, f"action {name}")
    assert seen > 0, "domain.pddl has no actions"
    assert seen == len(_actions())


def test_every_link_is_cited():
    count = 0
    for line in PROBLEM.read_text().splitlines():
        if LINK_LINE_RE.search(line.split(";", 1)[0]):
            count += 1
            assert "; src:" in line, f"link fact without a trailing citation: {line.strip()!r}"
            _check_src_line(line[line.index("; src:"):], f"link {line.strip().split(';')[0]}")
    assert count == len(_problem_links()) > 0


def test_goal_is_cited():
    seg = load_segment("part1")
    assert len(seg.goal) == len(seg.goal_cite) > 0
    assert seg.goal == [{"bit": 85, "eq": 1}, {"bit": 86, "eq": 1}]
    assert seg.inventory is not None
    assert (seg.inventory["verb_first"], seg.inventory["count"], seg.inventory["var_first"]) == (200, 8, 133)
    assert seg.start and {"room": 33} in seg.start


def test_steps_entries_are_cited():
    for key, entry in _steps()["actions"].items():
        assert isinstance(entry.get("cite"), str) and entry["cite"].strip(), f"steps.toml {key!r} has no cite"


# --- PDDL subset and costs -------------------------------------------------------------


def test_problem_has_metric():
    text = _strip_comments(PROBLEM.read_text())
    assert re.search(r"\(:metric\s+minimize\s+\(total-cost\)\)", text)
    assert re.search(r"\(=\s*\(total-cost\)\s+0\)", text)


def test_domain_uses_lmcut_safe_subset():
    tree = _domain_tree()
    reqs = set(_section(tree, ":requirements")[1:])
    assert reqs <= ALLOWED_REQUIREMENTS, f"unsupported requirements {reqs - ALLOWED_REQUIREMENTS}"
    for name, action in _actions().items():
        for sub in _walk(action):
            assert not (sub and sub[0] in FORBIDDEN_KEYWORDS), f"action {name} uses {sub[0]!r}"
        effect = _keyword_value(action, ":effect")
        costs = [s for s in _walk(effect) if s and s[0] == "increase"]
        assert costs == [["increase", ["total-cost"], "1"]], f"action {name} must cost exactly 1, got {costs}"


def test_atoms_use_declared_predicates_and_constants():
    tree = _domain_tree()
    # Arity = number of ?variables in the declaration (type names are not arguments).
    preds ={p[0]: sum(1 for t in p[1:] if t.startswith("?")) for p in _section(tree, ":predicates")[1:]}
    consts = _section(tree, ":constants")[1:]
    constants = {c for c in consts if c != "-"}
    for name, action in _actions().items():
        params = _keyword_value(action, ":parameters")
        variables = {t for t in params if t.startswith("?")}
        for part in (":precondition", ":effect"):
            for _, atom in _atoms(_keyword_value(action, part)):
                assert atom[0] in preds, f"action {name}: undeclared predicate {atom[0]}"
                assert len(atom) - 1 == preds[atom[0]], f"action {name}: wrong arity in {atom}"
                for arg in atom[1:]:
                    assert arg in variables or arg in constants, f"action {name}: unknown term {arg} in {atom}"
    init = _section(_parse_sexp(PROBLEM.read_text()), ":init")[1:]
    for fact in init:
        if fact[0] == "=":
            continue
        assert fact[0] in preds, f"problem: undeclared predicate {fact[0]}"
        for arg in fact[1:]:
            assert arg in constants, f"problem: unknown constant {arg} in {fact}"


# --- naming and step coverage ------------------------------------------------------


def test_transition_actions_are_named_walk():
    for name, action in _actions().items():
        moves = any(
            atom[0] == "at" for part in (":effect",) for _, atom in _atoms(_keyword_value(action, part))
        )
        assert moves == name.startswith("walk"), (
            f"action {name}: changes (at ...) = {moves}, but its name "
            f"{'does' if name.startswith('walk') else 'does not'} start with 'walk'"
        )


def test_only_walk_has_parameters():
    for name, action in _actions().items():
        params = _keyword_value(action, ":parameters")
        if name == "walk":
            assert params == ["?from", "?to", "-", "room"]
        else:
            assert params == [], f"action {name} has parameters {params}; only 'walk' may"


def test_every_link_has_step():
    actions = _steps()["actions"]
    links = _problem_links()
    assert len(set(links)) == len(links), "duplicate link facts"
    for a, b in links:
        assert f"walk {a} {b}" in actions, f"steps.toml has no template for link {a} -> {b}"


def test_every_domain_action_has_steps():
    actions = _steps()["actions"]
    names = set(_actions())
    for name in names - {"walk"}:
        assert name in actions, f"steps.toml has no template for action {name}"
    links = {f"walk {a} {b}" for a, b in _problem_links()}
    stale = [k for k in actions if k not in names and k not in links]
    assert not stale, f"steps.toml keys that match no ground action: {stale}"


def test_steps_resolve_against_script_index():
    _require_index()
    index = _script_index()
    steps = _steps()
    for key in steps["actions"]:
        compiled = compile_plan(Plan(actions=[tuple(key.split())], cost=1), steps, index)
        assert compiled, key
        for step in compiled:
            assert step["action"] == key


# --- the real planner ------------------------------------------------------------


@pytest.mark.requires_fd
def test_planner_finds_plan(fd_ready, tmp_path):
    plan = run_planner(DOMAIN, PROBLEM, tmp_path / "part1.sas_plan", time_limit_s=300)
    assert plan.actions
    assert plan.cost == len(plan.actions)  # every action costs 1
    steps = _steps()
    for action in plan.actions:
        assert " ".join(action) in steps["actions"], f"plan action {action} has no step template"
    _require_index()
    compiled = compile_plan(plan, steps, _script_index())
    assert len(compiled) >= len(plan.actions)
