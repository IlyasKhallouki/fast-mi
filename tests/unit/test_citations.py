"""The Phase 7 fragment validator (``speedrun.citations``) on synthetic fragments and a synthetic script dump."""

import pytest
from _extract_toy import DOOR_SRC, FRAGMENTS, HALL, HALL_ACTIONS, HAND_DOMAIN, YARD, YARD_ACTIONS, action, make_scripts

from speedrun.citations import (
    Click,
    Sentence,
    check_fragment,
    check_fragments,
    citation_problem,
    filter_fragment,
    filter_fragments,
    parse_atom,
    parse_fragment,
)


@pytest.fixture
def scripts(tmp_path):
    return make_scripts(tmp_path / "scripts")


def codes(issues) -> list[str]:
    return [i.code for i in issues]


# --- valid fragments ---------------------------------------------------------------


def test_valid_fragments_have_no_issues(scripts):
    assert check_fragment(YARD, scripts) == []
    assert check_fragment(HALL, scripts) == []
    assert check_fragments(FRAGMENTS, scripts) == []


def test_parse_reads_the_annotations():
    frag = parse_fragment(HALL)
    assert frag.issues == []
    assert [a.name for a in frag.actions] == HALL_ACTIONS
    chest = frag.actions[0]
    assert [(c.file, c.offset) for c in chest.cites] == [
        ("room-091-hall/obj-0902-chest.txt", "0010"),
        ("room-091-hall/obj-0902-chest.txt", "0015"),
    ]
    assert chest.input == Sentence(verb=9, obj=902, obj2=0)
    assert chest.room == 91
    assert chest.dialogue == ["yes please", "thanks"]
    assert chest.pre == [(True, "at-r91"), (False, "bit-85"), (True, "var-54-eq--80")]
    assert chest.eff == [(True, "bit-85"), (True, "has-o902")]
    give = frag.actions[1]
    assert give.input == Sentence(verb=4, obj=904, obj2=905)
    wave = frag.actions[-1]
    assert wave.input == Click(verb=7, inventory=904, offset=-1)


def test_action_text_keeps_its_annotation_block():
    frag = parse_fragment(YARD)
    # The block is every comment line directly above "(:action", free comments included.
    first = frag.actions[0].text
    assert first.startswith(";; Toy yard (room 90)")
    assert "; src: data/scripts/room-090-yard/obj-0904-coin.txt [0010]" in first
    assert first.endswith("(increase (total-cost) 1)))")
    second = frag.actions[1].text
    assert second.startswith("; src: data/scripts/room-090-yard/obj-0901-door.txt [0010]")
    assert "pick-up-coin" not in second


def test_free_comments_use_two_semicolons(scripts):
    text = action("a", extra=(";; a free note: anything goes here",))
    assert check_fragment(text, scripts) == []


def test_click_without_offset(scripts):
    text = action("a", inputs=("; click: 7,inv:904",))
    assert check_fragment(text, scripts) == []
    assert parse_fragment(text).actions[0].input == Click(verb=7, inventory=904, offset=0)


def test_missing_precondition_is_allowed(scripts):
    assert check_fragment(action("a", pre=None), scripts) == []


# --- citations ---------------------------------------------------------------------


def test_missing_src_is_rejected(scripts):
    issues = check_fragment(action("uncited", src=()), scripts)
    assert codes(issues) == ["no-src"]
    assert issues[0].action == "uncited"


def test_src_separated_by_a_blank_line_does_not_count(scripts):
    text = action("a", src=()).replace("; sentence", DOOR_SRC + "\n\n; sentence")
    assert "no-src" in codes(check_fragment(text, scripts))


@pytest.mark.parametrize(
    "line",
    [
        "; src: data/scripts/room-090-yard/obj-0901-door.txt [0010]",  # no "— text"
        "; src: data/scripts/room-090-yard/obj-0901-door.txt [10] — short offset",
        "; src: data/scripts/room-090-yard/obj-0901-door.txt [001e] — lower-case hex",
        "; src: scripts/room-090-yard/obj-0901-door.txt [0010] — not under data/scripts",
        ";src: data/scripts/room-090-yard/obj-0901-door.txt [0010] — no space",
    ],
)
def test_malformed_src_is_rejected(scripts, line):
    assert "bad-src" in codes(check_fragment(action("a", src=(line,)), scripts))


def test_nonexistent_file_is_rejected(scripts):
    line = "; src: data/scripts/room-090-yard/obj-0999-nothing.txt [0010] — no such object"
    issues = check_fragment(action("a", src=(line,)), scripts)
    assert codes(issues) == ["missing-file"]
    assert "obj-0999-nothing.txt" in issues[0].message


def test_file_outside_the_scripts_dir_is_rejected(scripts):
    (scripts.parent / "secret.txt").write_text("[0010] x\n")
    line = "; src: data/scripts/../secret.txt [0010] — escapes"
    assert codes(check_fragment(action("a", src=(line,)), scripts)) == ["missing-file"]


def test_bad_offset_is_rejected(scripts):
    line = "; src: data/scripts/room-090-yard/obj-0901-door.txt [0011] — no instruction there"
    issues = check_fragment(action("a", src=(line,)), scripts)
    assert codes(issues) == ["bad-offset"]
    assert "[0011]" in issues[0].message


def test_every_src_line_is_checked(scripts):
    bad = "; src: data/scripts/room-090-yard/obj-0901-door.txt [0011] — wrong"
    assert codes(check_fragment(action("a", src=(DOOR_SRC, bad)), scripts)) == ["bad-offset"]


def test_without_a_scripts_dir_files_are_not_checked():
    line = "; src: data/scripts/room-090-yard/obj-0999-nothing.txt [0010] — not checked"
    assert check_fragment(action("a", src=(line,)), None) == []


def test_citation_problem_helper(scripts):
    assert citation_problem(scripts, "room-090-yard/obj-0901-door.txt", "0010") is None
    missing = citation_problem(scripts, "room-090-yard/nope.txt", "0010")
    assert missing.code == "missing-file" and str(missing) == "cited file room-090-yard/nope.txt does not exist"
    offset = citation_problem(scripts, "room-090-yard/obj-0901-door.txt", "0011")
    assert offset.code == "bad-offset"
    assert str(offset) == "offset [0011] does not occur in room-090-yard/obj-0901-door.txt"


# --- player input, room, dialogue ------------------------------------------------------


def test_two_input_lines_are_rejected(scripts):
    text = action("a", inputs=("; sentence: 2 901", "; sentence: 11 901"))
    assert codes(check_fragment(text, scripts)) == ["multiple-inputs"]


def test_sentence_and_click_are_two_inputs(scripts):
    text = action("a", inputs=("; sentence: 2 901", "; click: 7,inv:904,-1"))
    assert codes(check_fragment(text, scripts)) == ["multiple-inputs"]


def test_missing_input_is_rejected(scripts):
    assert codes(check_fragment(action("a", inputs=()), scripts)) == ["no-input"]


@pytest.mark.parametrize(
    "line,code",
    [
        ("; sentence: 18 901", "bad-sentence"),  # verb 18 (Tease) is not a player verb
        ("; sentence: 2", "bad-sentence"),
        ("; sentence: 2 901 0", "bad-sentence"),  # objB 0 means none: leave it out
        ("; sentence: open door", "bad-sentence"),
        ("; click: 7,inv:904,0", "bad-click"),  # offset 0 means none: leave it out
        ("; click: 7,904", "bad-click"),
        ("; click: 99,inv:904", "bad-click"),
    ],
)
def test_malformed_input_is_rejected(scripts, line, code):
    assert code in codes(check_fragment(action("a", inputs=(line,)), scripts))


def test_missing_room_is_rejected(scripts):
    assert codes(check_fragment(action("a", room=None), scripts)) == ["no-room"]


def test_two_rooms_are_rejected(scripts):
    assert codes(check_fragment(action("a", extra=("; room: 90",)), scripts)) == ["multiple-rooms"]


def test_room_must_match_the_at_precondition(scripts):
    issues = check_fragment(action("a", room="; room: 91"), scripts)
    assert codes(issues) == ["room-mismatch"]
    two = action("b", pre="(and (at-r90) (at-r91))")
    assert codes(check_fragment(two, scripts)) == ["room-mismatch"]


def test_room_without_an_at_precondition_is_accepted(scripts):
    assert check_fragment(action("a", pre="(and (has-o904))"), scripts) == []


def test_bad_room_is_rejected(scripts):
    assert codes(check_fragment(action("a", room="; room: yard"), scripts)) == ["bad-room"]


def test_dialogue_must_be_ascii(scripts):
    issues = check_fragment(action("a", extra=("; dialogue: Mêlée",)), scripts)
    assert codes(issues) == ["bad-dialogue"]


def test_unknown_annotation_is_rejected(scripts):
    issues = check_fragment(action("a", extra=("; sentense: 2 901",)), scripts)
    assert codes(issues) == ["bad-annotation"]
    assert ";;" in issues[0].message  # tells the extractor how to write a free comment


# --- vocabulary, structure, cost -------------------------------------------------------


@pytest.mark.parametrize(
    "atom",
    [
        "door-open",  # an abstract predicate
        "state-o901-16",  # states are 0..15
        "bit-085",  # leading zero: would not merge with bit-85
        "class-o905-0",  # classes are 1..32
        "owner-o904-16",  # owners are 0..15
        "var-195-gt-100",
        "at r90",  # an argument
    ],
)
def test_unknown_atom_is_rejected(scripts, atom):
    issues = check_fragment(action("a", pre=f"(and (at-r90) ({atom}))"), scripts)
    assert codes(issues) == ["unknown-atom"]


def test_unknown_atom_in_an_effect_is_rejected(scripts):
    eff = "(and (door-open) (increase (total-cost) 1))"
    assert codes(check_fragment(action("a", eff=eff), scripts)) == ["unknown-atom"]


def test_vocabulary():
    assert parse_atom("at-r215") == ("at", (215,))
    assert parse_atom("has-o904") == ("has", (904,))
    assert parse_atom("bit-85") == ("bit", (85,))
    assert parse_atom("state-o901-15") == ("state", (901, 15))
    assert parse_atom("owner-o904-15") == ("owner", (904, 15))
    assert parse_atom("class-o905-32") == ("class", (905, 32))
    assert parse_atom("var-195-eq-0") == ("var-eq", (195, 0))
    assert parse_atom("var-54-eq--80") == ("var-eq", (54, -80))
    assert parse_atom("var-195-ge-478") == ("var-ge", (195, 478))
    for bad in ("bit-85x", "var-195-eq--0", "at-r", "has-904", "link"):
        assert parse_atom(bad) is None, bad


def test_missing_cost_is_rejected(scripts):
    eff = "(and (not (state-o901-0)) (state-o901-1))"
    assert codes(check_fragment(action("a", eff=eff), scripts)) == ["no-cost"]


@pytest.mark.parametrize(
    "cost", ["(increase (total-cost) 2)", "(increase (total-cost) 1) (increase (total-cost) 1)"]
)
def test_other_costs_are_rejected(scripts, cost):
    eff = f"(and (state-o901-1) {cost})"
    assert codes(check_fragment(action("a", eff=eff), scripts)) == ["bad-cost"]


def test_parameters_are_rejected(scripts):
    assert codes(check_fragment(action("a", params="(?r)"), scripts)) == ["parameters"]


def test_empty_parameters_are_accepted(scripts):
    assert check_fragment(action("a", params="()"), scripts) == []


@pytest.mark.parametrize(
    "eff",
    [
        "(and (when (bit-85) (bit-86)) (increase (total-cost) 1))",
        "(and (forall (?x) (bit-86)) (increase (total-cost) 1))",
    ],
)
def test_unsupported_effects_are_rejected(scripts, eff):
    assert "unsupported" in codes(check_fragment(action("a", eff=eff), scripts))


def test_disjunctive_precondition_is_rejected(scripts):
    pre = "(and (at-r90) (or (bit-85) (bit-86)))"
    assert "unsupported" in codes(check_fragment(action("a", pre=pre), scripts))


def test_cost_in_the_precondition_is_rejected(scripts):
    pre = "(and (at-r90) (increase (total-cost) 1))"
    assert "bad-structure" in codes(check_fragment(action("a", pre=pre), scripts))


def test_unknown_action_keyword_is_rejected(scripts):
    text = action("a").replace("  :effect", "  :duration 3\n  :effect")
    assert "bad-structure" in codes(check_fragment(text, scripts))


# --- names and layout ----------------------------------------------------------------


def test_duplicate_name_in_one_fragment_rejects_every_copy(scripts):
    issues = check_fragment(action("same") + "\n" + action("same"), scripts)
    assert codes(issues) == ["duplicate-name", "duplicate-name"]


def test_duplicate_name_against_other_fragments(scripts):
    issues = check_fragment(action("open-door"), scripts, other_names={"open-door": "yard.pddl"})
    assert codes(issues) == ["duplicate-name"]
    assert "yard.pddl" in issues[0].message


def test_duplicate_name_across_fragments_rejects_both(scripts):
    issues = check_fragments({"a.pddl": action("same"), "b.pddl": action("same")}, scripts)
    assert codes(issues) == ["duplicate-name", "duplicate-name"]
    assert {i.source for i in issues} == {"a.pddl", "b.pddl"}


def test_names_are_case_insensitive(scripts):
    issues = check_fragment(action("Same") + "\n" + action("same"), scripts)
    assert codes(issues) == ["duplicate-name", "duplicate-name"]


def test_unbalanced_parentheses_is_a_parse_error(scripts):
    issues = check_fragment(action("a").rstrip()[:-1], scripts)
    assert codes(issues) == ["parse"]


def test_only_actions_at_top_level(scripts):
    text = "(define (domain x))\n" + action("a")
    issues = check_fragment(text, scripts)
    assert codes(issues) == ["not-action"]
    assert issues[0].action is None and issues[0].line == 1


def test_action_must_start_its_line(scripts):
    text = action("a").rstrip() + " " + action("b", src=(), inputs=(), room=None).lstrip()
    assert "layout" in codes(check_fragment(text, scripts))


def test_issue_str_names_source_line_and_action(scripts):
    (issue,) = check_fragment(action("a", src=()), scripts, source="out/extract/part1/bar.pddl")
    text = str(issue)
    assert text.startswith("out/extract/part1/bar.pddl:")
    assert "a" in text and "no-src" in text


# --- filtering -------------------------------------------------------------------------


def test_filter_drops_rejected_actions_and_keeps_the_rest(scripts):
    text = YARD + "\n" + action("uncited", src=()) + "\n" + action("costless", eff="(and (state-o901-1))")
    accepted, rejected = filter_fragment(text, scripts)
    assert [name for name, _ in rejected] == ["uncited", "costless"]
    assert [codes(issues) for _, issues in rejected] == [["no-src"], ["no-cost"]]
    frag = parse_fragment(accepted)
    assert [a.name for a in frag.actions] == YARD_ACTIONS
    assert check_fragment(accepted, scripts) == []
    assert "; src: data/scripts/room-090-yard/obj-0901-door.txt [0028] — then loadRoomWithEgo(903,91)" in accepted


def test_filter_of_an_unparseable_fragment_keeps_nothing(scripts):
    accepted, rejected = filter_fragment(YARD + "\n(:action broken\n", scripts)
    assert accepted.strip() == ""
    assert [codes(issues) for _, issues in rejected] == [["parse"]]


def test_filter_fragments_rejects_duplicates_in_both(scripts):
    frags = {"a.pddl": YARD, "b.pddl": action("open-door") + "\n" + action("fine")}
    accepted, rejected = filter_fragments(frags, scripts)
    assert sorted((src, name) for src, name, _ in rejected) == [("a.pddl", "open-door"), ("b.pddl", "open-door")]
    assert [a.name for a in parse_fragment(accepted["a.pddl"]).actions] == ["pick-up-coin", "walk-yard-to-hall"]
    assert [a.name for a in parse_fragment(accepted["b.pddl"]).actions] == ["fine"]


# --- citations-only mode (the hand-written domain) ----------------------------------------


def test_citations_only_accepts_a_hand_domain(scripts):
    assert check_fragment(HAND_DOMAIN, scripts, citations_only=True) == []


def test_hand_domain_fails_the_full_check(scripts):
    assert check_fragment(HAND_DOMAIN, scripts) != []


def test_citations_only_reports_citation_problems(scripts):
    text = HAND_DOMAIN.replace("obj-0906-bell.txt [0010]", "obj-0906-bell.txt [0011]")
    text = text.replace(
        "  ; src: data/scripts/room-091-hall/obj-0902-chest.txt [0015] — Bit[85]\n", "  ;; no citation\n"
    )
    issues = check_fragment(text, scripts, citations_only=True)
    assert sorted((i.action, i.code) for i in issues) == [("ring-bell", "bad-offset"), ("take-chest", "no-src")]


def test_citations_only_rejects_duplicate_names(scripts):
    text = HAND_DOMAIN.replace("(:action ring-bell", "(:action rub-coin")
    issues = check_fragment(text, scripts, citations_only=True)
    assert codes(issues) == ["duplicate-name", "duplicate-name"]


def test_repeated_keyword_is_rejected(scripts):
    text = action("a").replace("  :effect", "  :precondition (and (at-r90))\n  :effect")
    assert "bad-structure" in codes(check_fragment(text, scripts))
