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
from speedrun.citations import citation_problem
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
_SCRIPT_TEXT: dict = {}  # cited script files already read (citation_problem's cache)
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
# The cost-1-per-action optimum (docs/part1/model.md section 8). The time
# objective rewrites the costs in a copy of the model; the hand-written model
# keeps unit costs, and alternatives added for the time objective must not
# make the unit-cost plan cheaper by accident.
UNIT_COST_OPTIMUM = 66
# Split pairs (docs/part1/model.md section 14): the same sentence whose
# duration depends on one fact, so each half gets its own measured cost.
# (action that requires the fact false, action that requires it true, fact).
SPLIT_PAIRS = [
    # First exit through 315 plays the LeChuck "Meanwhile" cutscene and sets Bit[446]
    # (room-028-bar/obj-0315-door.txt [0080]-[008A]); later exits load the dock at once ([0090]).
    ("walk-out-of-bar-from-left-meanwhile", "walk-out-of-bar-from-left", "lechuck-cutscene-seen"),
    ("walk-out-of-bar-from-right-meanwhile", "walk-out-of-bar-from-right", "lechuck-cutscene-seen"),
    # After a provoked cook (room-028-bar/local-214.txt [004B] -> local-212.txt) the wait for him
    # is 600 jiffies instead of local-211's 1800-3000.
    ("walk-into-kitchen", "walk-into-kitchen-after-provoking-cook", "cook-provoked"),
    # Bit[85] is set at room-042-underwate/local-200.txt [0041]; when the treasure is already done
    # the goal holds there and the Elaine scene in room 83 never plays.
    ("walk-up-ladder-taking-idol", "walk-up-ladder-taking-idol-last", "treasure-trial-done"),
]
# The storekeeper as guide (docs/part1/model.md section 14): global 67 walks him
# store -> 34 -> 35 -> 33 -> 85 -> 218 -> 215 -> 203, waiting in each room until
# VAR_ROOM is his room and giving up after 1800 jiffies (3600 in 33 and 85)
# (global/script-067.txt [000D]-[0128], [02E3], [035A]). The model follows him
# with no detour: these are the nodes on his path, and the only actions allowed
# there while (following-storekeeper) holds.
FOLLOW_NODES = {"store", "high-street-town", "low-street", "dock", "lookout", "melee-map", "f218", "f215"}
FOLLOW_ACTIONS = {
    "open-store-door-from-inside",
    "walk-out-of-store",
    "walk-follow-guide-to-low-street",
    "walk-follow-guide-to-dock",
    "walk-follow-guide-to-lookout",
    "walk-follow-guide-to-map",
    "walk-follow-guide-to-f218",
    "walk-follow-guide-to-f215",
    "walk-forest-gate-215-203-with-guide",
    # Instant or nearly so (6-78 ticks), far inside the 1800-jiffy limit.
    "pick-up-petal",
    "drug-meat-with-petal",
    "open-cake",
}
# Alternative exit objects found by the blind extraction (docs/extraction-diff.md
# section 3; docs/part1/model.md section 14.8): a second object that makes the
# same transition as an existing link from another walk point, so its duration
# may differ. (alternative action, twin ground action, object id)
ALT_EXITS = [
    # Path 686 forwards every verb to 685's Walk to (room-058-damnfores/obj-0686-path.txt [0010]);
    # 218 and 220 draw it next to 685 (entry.txt [08E5]/[08ED], [09B9]/[09C1]).
    ("walk-f218-f215-via-686", "walk f218 f215", 686),
    ("walk-f220-f210-via-686", "walk f220 f210", 686),
    # Dock 905 does what 904 does while !Bit[453], landing at x 566 instead of 308
    # (room-083-cu-dock/obj-0905-dock.txt [0010]-[0020]; obj-0904-dock.txt [0019]).
    ("walk-cu-dock-dock-via-905", "walk cu-dock dock", 905),
]


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
        problem = citation_problem(SCRIPTS, rel, offset, _SCRIPT_TEXT)
        assert problem is None, f"{where}: {problem}"


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


def _ground_actions() -> dict[str, tuple[set, set, set, set]]:
    """Every ground action key -> (positive pre, negative pre, add, delete) atom sets."""

    def split(expr) -> tuple[set, set]:
        atoms = _atoms(expr)
        return {tuple(a) for pos, a in atoms if pos}, {tuple(a) for pos, a in atoms if not pos}

    out = {}
    for name, action in _actions().items():
        pre, neg = split(_keyword_value(action, ":precondition"))
        add, dele = split(_keyword_value(action, ":effect"))
        if name == "walk":
            for a, b in _problem_links():
                bind = {"?from": a, "?to": b}
                ground = lambda atoms: {tuple(bind.get(t, t) for t in atom) for atom in atoms}  # noqa: E731
                out[f"walk {a} {b}"] = (ground(pre), ground(neg), ground(add), ground(dele))
        else:
            out[name] = (pre, neg, add, dele)
    return out


def _enables(a: tuple[set, set, set, set], b: tuple[set, set, set, set]) -> bool:
    """A adds a fact B requires, and B is still applicable right after A (as far as A's effects tell)."""
    _, _, add_a, del_a = a
    pre_b, neg_b, _, _ = b
    if not add_a & pre_b or add_a & neg_b or del_a & pre_b:
        return False
    at_a = {f for f in add_a if f[0] == "at"}
    at_b = {f for f in pre_b if f[0] == "at"}
    return not (at_a and at_b and not at_a & at_b)


def _compiled_templates() -> dict[str, list[dict]]:
    index = _script_index()
    steps = _steps()
    return {key: compile_plan(Plan(actions=[tuple(key.split())], cost=1), steps, index) for key in steps["actions"]}


def test_no_consecutive_duplicate_sentences():
    """No action pushes the same sentence twice in a row, inside a template or across an enabling pair.

    The engine runs a repeated sentence twice, so a duplicate is either a
    wasted action (a defensive re-Open of an open door) or a second click that
    must be documented (DOUBLE_SENTENCE_ALLOWED). Across actions, A's last
    sentence is compared with B's first whenever A adds a fact B requires and
    leaves B applicable (A does not end elsewhere or add a fact B needs false),
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
    for a, ga in ground.items():
        last = _sentence(compiled[a][-1])
        if last is None:
            continue
        for b, gb in ground.items():
            if not _enables(ga, gb):
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


# --- alternatives and splits for the time objective (model.md section 14) -----------


def _pre(name: str) -> list[tuple[bool, list]]:
    return _atoms(_keyword_value(_actions()[name], ":precondition"))


def _eff(name: str) -> list[tuple[bool, list]]:
    return _atoms(_keyword_value(_actions()[name], ":effect"))


def _init_facts() -> list[list]:
    return [f for f in _section(_parse_sexp(PROBLEM.read_text()), ":init")[1:] if f[0] != "="]


def _may_run_in(name: str, rooms: set[str]) -> bool:
    """True unless the action's (at ...) precondition pins it to a node outside ``rooms``."""
    at = [atom[1] for pos, atom in _pre(name) if pos and atom[0] == "at"]
    return not at or any(r.startswith("?") or r in rooms for r in at)


def test_bar_exits_are_actions_not_links():
    """The bar exit is split on Bit[446], so it cannot stay a static link (a link carries no guard)."""
    links = set(_problem_links())
    assert ("bar-left", "dock") not in links
    assert ("bar-right", "dock") not in links
    for side in ("left", "right"):
        first, later = f"walk-out-of-bar-from-{side}-meanwhile", f"walk-out-of-bar-from-{side}"
        for name in (first, later):
            assert (True, ["at", f"bar-{side}"]) in _pre(name)
            assert (True, ["at", "dock"]) in _eff(name)
        assert (True, ["lechuck-cutscene-seen"]) in _eff(first)
    assert ["lechuck-cutscene-seen"] not in _init_facts()  # Bit[446] is clear at segment start


def test_split_pairs_have_complementary_guards():
    """Each split pair is one sentence; exactly one half applies in any state."""
    actions = _actions()
    steps = _steps()["actions"]
    for off, on, fact in SPLIT_PAIRS:
        assert off in actions and on in actions, (off, on)
        assert (False, [fact]) in _pre(off), f"{off} must require (not ({fact}))"
        assert (True, [fact]) in _pre(on), f"{on} must require ({fact})"
        assert steps[off]["steps"] == steps[on]["steps"], f"{off} and {on} must push the same steps"
        moves = lambda n: sorted((pos, a) for pos, a in _eff(n) if a[0] == "at")  # noqa: E731
        assert moves(off) == moves(on), f"{off} and {on} must move ego the same way"


def test_cook_provoked_is_used_at_once():
    """(cook-provoked) holds only between a provoking Open 316 and the kitchen walk it shortens.

    Open 316 while the cook is in the kitchen runs room-028-bar/local-214.txt, which starts
    local-212 ([004B]): the cook comes out 600 jiffies later. Only the kitchen walk may follow,
    so every other action that can run in the bar requires the fact false.
    """
    for name in _actions():
        if name == "walk-into-kitchen-after-provoking-cook" or not _may_run_in(name, {"bar-left", "bar-right"}):
            continue
        assert (False, ["cook-provoked"]) in _pre(name), (
            f"action {name} can run between a provoke and walk-into-kitchen-after-provoking-cook"
        )


def test_provoke_needs_a_fresh_cook_timer():
    """Provoking works only while this bar visit's local-211 timer runs (cook in the kitchen).

    walk-into-bar starts it (room-028-bar/local-205.txt [0040]-[0044]); a return from the
    kitchen brings the cook out at once ([0033]-[003A]), so every kitchen entry consumes it.
    """
    provokes = [n for n in _actions() if (True, ["cook-provoked"]) in _eff(n)]
    assert sorted(provokes) == ["provoke-cook", "walk-to-kitchen-door-provoking-cook"]
    for name in provokes:
        assert (True, ["cook-timer-fresh"]) in _pre(name)
    assert (True, ["cook-timer-fresh"]) in _eff("walk-into-bar")
    setters = [n for n in _actions() if (True, ["cook-timer-fresh"]) in _eff(n)]
    assert setters == ["walk-into-bar"]
    for name in _actions():
        if (True, ["at", "kitchen"]) in _eff(name):
            assert (True, ["cook-timer-fresh"]) in _pre(name), f"{name} must require (cook-timer-fresh)"
            assert (False, ["cook-timer-fresh"]) in _eff(name), f"{name} must delete (cook-timer-fresh)"


def test_following_the_storekeeper_is_isolated():
    """While global 67 guides, the plan walks his path and nothing else (no detour can outlast his timeout)."""
    for name in _actions():
        if name in FOLLOW_ACTIONS or not _may_run_in(name, FOLLOW_NODES):
            continue
        assert (False, ["following-storekeeper"]) in _pre(name), (
            f"action {name} can run while the plan follows the storekeeper; add (not (following-storekeeper))"
        )
    starters = sorted(n for n in _actions() if (True, ["following-storekeeper"]) in _eff(n))
    assert starters == ["pay-for-shovel-and-mints-ask-guide", "pay-for-shovel-ask-guide"]
    enders = [n for n in _actions() if (False, ["following-storekeeper"]) in _eff(n)]
    assert enders == ["walk-forest-gate-215-203-with-guide"]
    for name in FOLLOW_ACTIONS:
        if name.startswith("walk-follow-guide") or name == "walk-forest-gate-215-203-with-guide":
            assert (True, ["following-storekeeper"]) in _pre(name), name
    # The gate is passed with 685 only: 688 at 215 has no script-67 exemption
    # (room-058-damnfores/obj-0688-path.txt [004F]-[006B] vs obj-0685-path.txt [005B]).
    assert (True, ["at", "f203"]) in _eff("walk-forest-gate-215-203-with-guide")
    assert (True, ["forest-gate-open"]) in _eff("walk-forest-gate-215-203-with-guide")


def test_store_menu_with_the_guide_topic():
    """Once the leaders were asked (Var[199]), the store menu shows topic 122 after the purchases.

    It must be chosen (it ends the dialogue at room-030-store/local-211.txt [1138]); the
    old pay variants' choose lists would leave it in the menu, so they are barred.
    """
    steps = _steps()["actions"]
    pays = [n for n in _actions() if (True, ["shovel-unpaid"]) in _pre(n) and (True, ["has", "shovel"]) in _eff(n)]
    assert len(pays) == 6
    for name in pays:
        guided = (True, ["following-storekeeper"]) in _eff(name)
        assert (guided, ["sword-master-asked"]) in _pre(name), name
        assert (steps[name]["steps"][-1]["choose"][-1] == "Sword Master") == guided, name
        if guided:
            assert (True, ["store-door-387-closed"]) in _eff(name)  # local-211.txt [1122] closes 387


def test_pirate_leaders_talk_is_the_first_meeting():
    """The choose list fits only the first talk with no trial done (room-028-bar/local-220.txt [02B2])."""
    pre = _pre("talk-to-pirate-leaders")
    for fact in (["sword-master-asked"], ["idol-trial-done"], ["treasure-trial-done"], ["cook-timer-fresh"]):
        assert (False, fact) in pre, fact
    assert (True, ["at", "bar-right"]) in pre  # walk point (473,128), right half
    assert (True, ["sword-master-asked"]) in _eff("talk-to-pirate-leaders")
    gate_open = sorted(n for n in _actions() if (True, ["forest-gate-open"]) in _pre(n))
    assert gate_open == ["walk-forest-gate-215-203-open", "walk-forest-gate-215-220-open"]


def test_alternative_exits_mirror_their_twins():
    """Each alternative exit is its twin link with another object: same guards, same effects, same step shape.

    The generic walk's guards (store door, provoke, storekeeper) carry over, so the
    alternative is applicable exactly where its twin is, and it moves ego the same way.
    """
    ground = _ground_actions()
    steps = _steps()["actions"]
    for alt, twin, oid in ALT_EXITS:
        assert alt in ground, f"{alt} is not a domain action"
        _, a, b = twin.split()
        pre, neg, add, dele = ground[twin]
        assert ground[alt] == (pre - {("link", a, b)}, neg, add, dele), f"{alt} must mirror {twin}"
        assert alt in steps, f"steps.toml has no template for {alt}"
        (alt_step,) = steps[alt]["steps"]
        (twin_step,) = steps[twin]["steps"]
        assert alt_step["obj"]["id"] == oid, alt
        assert alt_step["obj"]["id"] != twin_step["obj"]["id"], alt
        same_object = {**alt_step, "obj": {**alt_step["obj"], "id": twin_step["obj"]["id"]}}
        assert same_object == twin_step, f"{alt} must push {twin}'s step on object {oid}"


def test_alternative_exits_compile_to_their_object():
    _require_index()
    compiled = _compiled_templates()
    for alt, twin, oid in ALT_EXITS:
        assert [s["obj"] for s in compiled[alt]] == [oid], alt
        assert _sentence(compiled[alt][0]) != _sentence(compiled[twin][0]), alt


def test_steal_idol_needs_only_the_opened_cake():
    """Walk to 637 tests only 420's owner and class 6 (room-053-foyer/obj-0637-gaping-hole.txt [000C]-[0021]).

    The theft (local-211) passes 641 and 642 only to the sentence-line helper local-218, which
    tests no owner, and then hides both whether or not ego holds them (local-211.txt
    [0088]/[008C], [00E3]/[00E7]), as it hides the file 420 ([0174]/[0178]).
    """
    pre = _pre("steal-idol")
    assert (True, ["has", "manual"]) not in pre
    assert (True, ["has", "lips"]) not in pre
    for fact in (["at", "foyer"], ["idol-room-visited"], ["has", "cake"], ["cake-opened"]):
        assert (True, fact) in pre, fact
    eff = _eff("steal-idol")
    for item in ("manual", "lips", "cake"):
        assert (False, ["has", item]) in eff, item
    assert (True, ["has", "foyer-idol"]) in eff


def test_breath_gives_keep_the_item():
    """A refused give still sets Bit[420] (room-031-jail/local-203.txt [029D] -> [0351]) and takes nothing."""
    learners = [n for n in _actions() if (True, ["otis-breath-known"]) in _eff(n)]
    assert sorted(learners) == ["give-meat-to-prisoner", "give-repellent-to-prisoner-before-mints", "talk-to-prisoner"]
    for name in learners:
        assert (False, ["otis-breath-known"]) in _pre(name)
        assert not [a for pos, a in _eff(name) if not pos and a[0] == "has"], f"{name} must keep every item"


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
    assert plan.cost == UNIT_COST_OPTIMUM
    steps = _steps()
    for action in plan.actions:
        assert " ".join(action) in steps["actions"], f"plan action {action} has no step template"
    _require_index()
    compiled = compile_plan(plan, steps, _script_index())
    assert len(compiled) >= len(plan.actions)
