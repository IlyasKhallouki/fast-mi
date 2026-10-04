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
# Actions that may push the same sentence twice in a row. Room 52 cancels the
# first walk to the circus tent with doSentence(STOP) once ego is in walkbox 7
# at x > 200 (data/scripts/room-052-circus-gr/local-202.txt [0000]), so a
# player clicks the tent twice (docs/part1/model.md section 12).
DOUBLE_SENTENCE_ALLOWED = {"walk-into-tent-with-pot"}
# Pairs of different actions that push the same sentence back to back because
# the first changes the state its object script branches on. Walk to 387:
# room-030-store/local-204.txt [0031] counts unpaid items; with the shovel
# unpaid the walk ends in the store menu ([004E]-[042B]), once it is paid the
# same walk leaves the store ([0044]).
REPEATED_SENTENCE_PAIRS = {
    (pay, "walk-out-of-store")
    for pay in (
        "pay-for-shovel",
        "pay-for-shovel-files-topic",
        "pay-for-shovel-and-mints",
        "pay-for-shovel-and-mints-files-topic",
    )
}


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


# --- one player sentence = one action ------------------------------------------------


def _sentence(step: dict) -> tuple | None:
    """A compiled step's sentence as (verb, obj, obj2, where), or None for click/dialogue-only steps.

    ``where`` is the step's room, or for forest steps (no ``room``) the pseudo-room
    they wait on in VAR_ROOM (var 4), so the same path object in two pseudo-rooms
    is two different sentences.
    """
    if "verb" not in step:
        return None
    where = step.get("room")
    if where is None:
        where = next((c["eq"] for c in step.get("until", []) if c.get("var") == 4 and "eq" in c), None)
    return (step["verb"], step["obj"], step.get("obj2", 0), where)


def _ground_actions() -> dict[str, tuple[set, set]]:
    """Every ground action key -> (positive precondition atoms, add effect atoms)."""
    out = {}
    for name, action in _actions().items():
        if name == "walk":
            continue
        pre = {tuple(a) for pos, a in _atoms(_keyword_value(action, ":precondition")) if pos}
        add = {tuple(a) for pos, a in _atoms(_keyword_value(action, ":effect")) if pos}
        out[name] = (pre, add)
    for a, b in _problem_links():
        out[f"walk {a} {b}"] = ({("at", a), ("link", a, b)}, {("at", b)})
    return out


def _compiled_templates() -> dict[str, list[dict]]:
    index = _script_index()
    steps = _steps()
    return {key: compile_plan(Plan(actions=[tuple(key.split())], cost=1), steps, index) for key in steps["actions"]}


def test_no_consecutive_duplicate_sentences():
    """No action pushes the same sentence twice in a row, inside a template or across an enabling pair.

    The engine runs a repeated sentence twice, so a duplicate is either a
    wasted action (a defensive re-Open of an open door) or a second click that
    must be documented (DOUBLE_SENTENCE_ALLOWED). Across actions, A's last
    sentence is compared with B's first whenever A adds a fact B requires,
    e.g. open-store-door -> walk-into-store.
    """
    _require_index()
    compiled = _compiled_templates()
    bad = []
    for key, steps in compiled.items():
        sentences = [_sentence(s) for s in steps]
        for i in range(1, len(sentences)):
            if sentences[i] is not None and sentences[i] == sentences[i - 1] and key not in DOUBLE_SENTENCE_ALLOWED:
                bad.append(f"{key!r} steps {i - 1} and {i} push {sentences[i]}")
    ground = _ground_actions()
    for a, (_, add_a) in ground.items():
        last = _sentence(compiled[a][-1])
        if last is None:
            continue
        for b, (pre_b, _) in ground.items():
            if not add_a & pre_b:
                continue
            # A walk straight back (the bar curtain 323 both ways) is never in an optimal plan.
            if a.startswith("walk ") and b.split()[1:] == a.split()[:0:-1]:
                continue
            if _sentence(compiled[b][0]) == last:
                bad.append(f"{a!r} ends and {b!r} (which it enables) starts with {last}")
    assert not bad, "consecutive duplicate sentences:\n" + "\n".join(bad)


def test_store_door_open_is_used_at_once():
    """(store-door-open) cannot outlive the next action, so walk-into-store needs no defensive Open.

    High Street citizens close 437 again (room-034-high-stre/local-200.txt
    [0053], [00CC]), so every action that can run in the town half of High
    Street, other than the two door actions themselves, requires the door fact
    false: open-store-door must be followed directly by walk-into-store.
    """
    for name, action in _actions().items():
        if name in {"open-store-door", "walk-into-store"}:
            continue
        pre = _atoms(_keyword_value(action, ":precondition"))
        rooms = [atom[1] for pos, atom in pre if pos and atom[0] == "at"]
        if rooms and all(not r.startswith("?") and r != "high-street-town" for r in rooms):
            continue  # never applicable in high-street-town
        assert (False, ["store-door-open"]) in pre, (
            f"action {name} can run between open-store-door and walk-into-store; add (not (store-door-open))"
        )


# --- the real planner ------------------------------------------------------------


@pytest.fixture(scope="module")
def optimal_plan(fd_ready, tmp_path_factory) -> Plan:
    return run_planner(DOMAIN, PROBLEM, tmp_path_factory.mktemp("part1") / "part1.sas_plan", time_limit_s=300)


@pytest.mark.requires_fd
def test_optimal_plan_has_no_consecutive_duplicate_sentences(optimal_plan: Plan):
    _require_index()
    compiled = compile_plan(optimal_plan, _steps(), _script_index())
    bad = []
    for i in range(1, len(compiled)):
        prev, cur = compiled[i - 1], compiled[i]
        same = _sentence(cur) is not None and _sentence(cur) == _sentence(prev)
        allowed = prev["action"] == cur["action"] in DOUBLE_SENTENCE_ALLOWED or (
            (prev["action"], cur["action"]) in REPEATED_SENTENCE_PAIRS
        )
        if same and not allowed:
            bad.append(f"steps {i - 1} ({prev['action']}) and {i} ({cur['action']}) push {_sentence(cur)}")
    assert not bad, "consecutive duplicate sentences in the compiled optimal plan:\n" + "\n".join(bad)


@pytest.mark.requires_fd
def test_planner_finds_plan(optimal_plan: Plan):
    plan = optimal_plan
    assert plan.actions
    assert plan.cost == len(plan.actions)  # every action costs 1
    steps = _steps()
    for action in plan.actions:
        assert " ".join(action) in steps["actions"], f"plan action {action} has no step template"
    _require_index()
    compiled = compile_plan(plan, steps, _script_index())
    assert len(compiled) >= len(plan.actions)
