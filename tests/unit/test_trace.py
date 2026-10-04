"""Unit tests for trace parsing and reporting (contract C5).

The fixtures under ``tests/fixtures/traces`` are synthetic and invented: room,
object and step names match the toy segment, and no text comes from the game.
They are ASCII JSON, like the bridge's output: bytes >= 0x80 are ``\\u00XX``
escapes of the game's cp437-like charset, decoded by ``speedrun.text``.
"""

import json
from pathlib import Path

import pytest

from speedrun.trace import (
    StepRecord,
    Trace,
    TraceError,
    format_changes,
    format_table,
    format_ticks,
    load_trace,
    summary,
)

TRACES = Path(__file__).resolve().parents[1] / "fixtures" / "traces"


def _load(name: str) -> Trace:
    return load_trace(TRACES / name)


def _write(tmp_path: Path, records: list[dict], name: str = "trace.jsonl") -> Path:
    path = tmp_path / name
    # ensure_ascii (the default) writes \u00XX escapes, exactly like the bridge.
    path.write_text("".join(json.dumps(r) + "\n" for r in records), encoding="ascii")
    return path


BOOT = {"type": "boot", "tick": 0, "frame": 0, "bridge": "speedrun-bridge v1", "audio_pump": True}


# --- load_trace: the ok trace ------------------------------------------------


def test_ok_trace_records():
    t = _load("ok.jsonl")
    assert t.boot["bridge"] == "speedrun-bridge v1"
    assert t.boot["audio_pump"] is True
    assert t.segment_start["tick0"] == 1000
    assert t.goal == {"type": "goal", "tick": 2360, "frame": 515, "ticks_from_start": 1360}
    assert t.end["reason"] == "goal"
    assert t.errors == []
    assert [s["reason"] for s in t.stalls] == ["sentence_script_running"]


def test_ok_trace_totals():
    t = _load("ok.jsonl")
    assert t.tick0 == 1000
    assert t.reached_goal is True
    assert t.total_ticks == 1360  # goal.tick - tick0


def test_ok_trace_steps():
    t = _load("ok.jsonl")
    assert [s.index for s in t.steps] == [0, 1, 2, 3]
    assert [s.action for s in t.steps] == ["answer-clerk", "take-widget", "wind-widget", "walk workshop office"]
    assert all(isinstance(s, StepRecord) for s in t.steps)

    take = t.steps[1]
    assert (take.start_tick, take.end_tick, take.duration) == (1010, 1250, 240)
    assert (take.room_start, take.room_end) == (101, 101)
    assert take.changes["inventory"]["added"] == [500]

    walk = t.steps[3]
    assert (walk.room_start, walk.room_end) == (101, 102)

    assert t.steps[0].choices == ["goodbye"]
    assert t.steps[0].clicks == []
    assert t.steps[2].clicks == [2, 300]
    assert t.steps[2].choices == []


def test_unknown_record_types_are_ignored():
    # ok.jsonl carries a "future_record" line; it must neither fail nor land anywhere.
    t = _load("ok.jsonl")
    assert len(t.steps) == 4
    assert t.errors == [] and len(t.stalls) == 1


def test_step_without_end_has_no_duration():
    t = _load("error.jsonl")
    failed = t.steps[1]
    assert failed.action == "buy-ledger"
    assert failed.start_tick == 810
    assert failed.end_tick is None and failed.room_end is None
    assert failed.duration is None


# --- errors, no goal ---------------------------------------------------------


def test_error_trace_surfaces_errors():
    t = _load("error.jsonl")
    assert t.reached_goal is False
    assert t.total_ticks is None
    assert t.end["reason"] == "error"
    assert len(t.errors) == 1
    err = t.errors[0]
    assert err["code"] == "room_mismatch"
    assert err["step"] == 1
    assert err["message"] == "expected room 102, ego in 101"


def test_error_summary_lists_errors():
    text = summary(_load("error.jsonl"))
    assert text.splitlines()[0] == "NO GOAL: end reason error"
    assert "room_mismatch" in text
    assert "expected room 102, ego in 101" in text
    assert "step 1" in text


def test_no_goal_trace():
    t = _load("no-goal.jsonl")
    assert t.goal is None
    assert t.reached_goal is False
    assert t.total_ticks is None
    assert t.errors == []
    assert t.end["reason"] == "plan_exhausted"
    assert summary(t).splitlines()[0] == "NO GOAL: end reason plan_exhausted"


def test_no_goal_summary_mentions_stalls():
    text = summary(_load("no-goal.jsonl"))
    assert "stall" in text and "cutscene" in text


def test_missing_end_record_is_reported_not_raised(tmp_path):
    seg = {"type": "segment_start", "tick": 10, "frame": 3, "tick0": 10, "room": 1}
    t = load_trace(_write(tmp_path, [BOOT, seg]))
    assert t.end is None
    assert t.reached_goal is False
    first = summary(t).splitlines()[0]
    assert first.startswith("NO GOAL:")
    assert "no end record" in first


# --- game text decoding -----------------------------------------------------


def test_choice_text_is_decoded_as_game_charset():
    t = _load("with-choice-highbytes.jsonl")
    # cp437 layout: 0x88 is "ê" and 0x82 is "é" (Mac Roman would give "à" and "Ç").
    assert t.steps[0].choices == ["a crêpe and a café", "yes"]


def test_error_message_is_decoded_as_game_charset():
    t = _load("with-choice-highbytes.jsonl")
    # 0x0F is the game's trademark sign.
    assert t.errors[0]["message"] == "no visible choice matches 'goodbye' (menu: Widget™, café au lait)"
    assert "Widget™, café au lait" in summary(t)


def test_decoding_falls_back_to_raw_text(tmp_path):
    # A code point above 0xFF cannot come from the bridge's Latin-1 escaping;
    # keep the string as is rather than failing.
    weird = "already ’ decoded"
    records = [
        BOOT,
        {"type": "step_start", "step": 0, "tick": 1, "frame": 1, "action": "a", "room": 1},
        {"type": "choice", "step": 0, "tick": 2, "frame": 2, "verb_id": 120, "text": weird},
        {"type": "error", "tick": 3, "frame": 3, "step": 0, "code": "engine_error", "message": weird},
        {"type": "end", "tick": 3, "frame": 3, "reason": "error"},
    ]
    t = load_trace(_write(tmp_path, records))
    assert t.steps[0].choices == [weird]
    assert t.errors[0]["message"] == weird


def test_non_string_text_does_not_crash(tmp_path):
    records = [
        BOOT,
        {"type": "error", "tick": 3, "frame": 3, "code": "engine_error", "message": None},
        {"type": "end", "tick": 3, "frame": 3, "reason": "error"},
    ]
    t = load_trace(_write(tmp_path, records))
    assert t.errors[0]["message"] is None
    assert "engine_error" in summary(t)


# --- TraceError --------------------------------------------------------------


def test_missing_file_raises(tmp_path):
    path = tmp_path / "nope.jsonl"
    with pytest.raises(TraceError, match="nope.jsonl"):
        load_trace(path)


@pytest.mark.parametrize("text", ["", "\n\n  \n"])
def test_empty_trace_raises(tmp_path, text):
    path = tmp_path / "trace.jsonl"
    path.write_text(text)
    with pytest.raises(TraceError, match="empty"):
        load_trace(path)


def test_truncated_trace_raises_with_line_number(tmp_path):
    path = _write(tmp_path, [BOOT])
    with path.open("a") as f:
        f.write('{"type":"end","tick":90')  # killed mid-write
    with pytest.raises(TraceError, match=r"line 2.*truncated"):
        load_trace(path)


def test_non_object_line_raises(tmp_path):
    path = tmp_path / "trace.jsonl"
    path.write_text(json.dumps(BOOT) + "\n[1, 2]\n")
    with pytest.raises(TraceError, match="line 2"):
        load_trace(path)


def test_record_without_type_raises(tmp_path):
    path = _write(tmp_path, [BOOT, {"tick": 5}])
    with pytest.raises(TraceError, match="line 2"):
        load_trace(path)


# --- format_ticks ------------------------------------------------------------


@pytest.mark.parametrize(
    ("ticks", "text"),
    [
        (0, "0:00.00"),
        (1, "0:00.02"),  # 1/60 s = 0.0167 s
        (60, "0:01.00"),
        (1360, "0:22.67"),
        (3600, "1:00.00"),
        (3599, "0:59.98"),
        (89398, "24:49.97"),
        (216000, "60:00.00"),  # minutes are not wrapped into hours
        (-900, "-0:15.00"),
    ],
)
def test_format_ticks(ticks, text):
    assert format_ticks(ticks) == text


def test_format_ticks_never_shows_sixty_seconds():
    for t in range(7200):
        seconds = format_ticks(t).split(":")[1]
        assert float(seconds) < 60, (t, format_ticks(t))


# --- format_changes ----------------------------------------------------------


def test_format_changes_compact():
    changes = {
        "vars": {"34": [0, 1], "35": [2, 5], "36": [0, 9]},
        "bits": {"85": [0, 1]},
        "inventory": {"added": [567], "removed": []},
        "room": [28, 41],
    }
    assert format_changes(changes) == "+inv 567, bits 85, vars 3, room 28→41"


def test_format_changes_removed_inventory_and_several_bits():
    changes = {"bits": {"86": [0, 1], "12": [1, 0]}, "inventory": {"added": [], "removed": [500]}}
    assert format_changes(changes) == "-inv 500, bits 12,86"


def test_format_changes_tolerates_missing_and_null_keys():
    assert format_changes({}) == ""
    assert format_changes(None) == ""
    assert format_changes({"vars": None, "bits": None, "inventory": None, "room": None}) == ""
    # An unchanged room is not a change.
    assert format_changes({"room": [101, 101], "vars": {}}) == ""


def test_format_changes_truncates_long_bit_lists():
    bits = {str(b): [0, 1] for b in range(1, 11)}
    text = format_changes({"bits": bits})
    assert text.startswith("bits 1,2,3,4,5,6")
    assert "+4 more" in text


# --- format_table ------------------------------------------------------------


def _rows(table: str) -> dict[str, str]:
    """Map each step's action to its table row."""
    rows = {}
    for line in table.splitlines():
        for action in ("answer-clerk", "take-widget", "wind-widget", "walk workshop office", "buy-ledger"):
            if action in line:
                rows[action] = line
    return rows


def test_format_table_header():
    header = format_table(_load("ok.jsonl")).splitlines()[0].split()
    assert header == ["#", "action", "room", "start", "end", "ticks", "changes"]


def test_format_table_relative_ticks():
    rows = _rows(format_table(_load("ok.jsonl")))
    # take-widget: 1010..1250 absolute, tick0 = 1000.
    take = rows["take-widget"].split()
    assert take[:6] == ["1", "take-widget", "101", "10", "250", "240"]
    walk = rows["walk workshop office"]
    assert " 610 " in walk and " 900 " in walk and " 290 " in walk
    assert "room 101→102" in walk


def test_format_table_step_before_segment_start_is_negative():
    rows = _rows(format_table(_load("ok.jsonl")))
    # 100..400 absolute with tick0 = 1000; no changes, so the row ends at ticks.
    assert rows["answer-clerk"].split() == ["0", "answer-clerk", "101", "-900", "-600", "300"]


def test_format_table_changes_column():
    rows = _rows(format_table(_load("ok.jsonl")))
    assert "+inv 500, bits 85, vars 2" in rows["take-widget"]
    assert "-inv 500, bits 12,86, vars 1" in rows["wind-widget"]


def test_format_table_has_legend():
    table = format_table(_load("ok.jsonl"))
    assert "bits" in table.splitlines()[-1] and "vars" in table.splitlines()[-1]


def test_format_table_unfinished_step():
    rows = _rows(format_table(_load("error.jsonl")))
    row = rows["buy-ledger"]
    assert " 310 " in row  # 810 - 500
    assert "no step_end" in row


def test_format_table_goal_mid_step_ends_at_goal(tmp_path):
    # C5 "Goal mid-step": the goal fires during the last step, so that step has
    # no step_end; the goal record closes it.
    records = [
        BOOT,
        {"type": "segment_start", "tick": 1000, "frame": 250, "tick0": 1000, "room": 101},
        {"type": "step_start", "step": 0, "tick": 1010, "frame": 253, "action": "take-widget", "room": 101},
        {"type": "step_end", "step": 0, "tick": 1250, "frame": 300, "room": 101, "changes": {}},
        {"type": "step_start", "step": 1, "tick": 1260, "frame": 303, "action": "wind-widget", "room": 101},
        {"type": "goal", "tick": 1500, "frame": 360, "ticks_from_start": 500},
        {"type": "end", "tick": 1500, "frame": 360, "reason": "goal", "room": 101},
    ]
    t = load_trace(_write(tmp_path, records))
    assert t.steps[1].end_tick is None  # the record itself stays unfinished
    row = _rows(format_table(t))["wind-widget"]
    # start 1260 - 1000, end = goal 1500 - 1000, ticks 1500 - 1260, changes "goal"
    assert row.split() == ["1", "wind-widget", "101", "260", "500", "240", "goal"]


def test_format_table_unfinished_last_step_without_goal_is_unknown(tmp_path):
    records = [
        BOOT,
        {"type": "segment_start", "tick": 1000, "frame": 250, "tick0": 1000, "room": 101},
        {"type": "step_start", "step": 0, "tick": 1260, "frame": 303, "action": "wind-widget", "room": 101},
        {"type": "end", "tick": 1500, "frame": 360, "reason": "max_ticks", "room": 101},
    ]
    row = _rows(format_table(load_trace(_write(tmp_path, records))))["wind-widget"]
    assert row.split()[:6] == ["0", "wind-widget", "101", "260", "?", "?"]
    assert "no step_end" in row


def test_format_table_without_segment_start_uses_absolute_ticks(tmp_path):
    records = [
        BOOT,
        {"type": "step_start", "step": 0, "tick": 100, "frame": 1, "action": "take-widget", "room": 1},
        {"type": "step_end", "step": 0, "tick": 160, "frame": 5, "room": 1, "changes": {}},
        {"type": "end", "tick": 200, "frame": 9, "reason": "plan_exhausted"},
    ]
    t = load_trace(_write(tmp_path, records))
    assert t.tick0 is None
    table = format_table(t)
    assert "absolute" in table
    row = _rows(table)["take-widget"]
    assert " 100 " in row and " 160 " in row


def test_format_table_no_steps():
    t = _load("no-goal.jsonl")
    t.steps.clear()
    assert "no steps" in format_table(t)


# --- summary -----------------------------------------------------------------


def test_summary_total():
    assert summary(_load("ok.jsonl")).splitlines()[0] == "TOTAL: 1360 ticks (0:22.67 at 60 Hz)"


def test_summary_goal_without_segment_start(tmp_path):
    records = [
        BOOT,
        {"type": "step_start", "step": 0, "tick": 100, "frame": 1, "action": "take-widget", "room": 1},
        {"type": "step_end", "step": 0, "tick": 160, "frame": 5, "room": 1, "changes": {}},
        {"type": "goal", "tick": 170, "frame": 6, "ticks_from_start": 170},
        {"type": "error", "tick": 171, "frame": 6, "code": "engine_error", "message": "late error"},
        {"type": "end", "tick": 200, "frame": 9, "reason": "goal"},
    ]
    t = load_trace(_write(tmp_path, records))
    assert t.reached_goal is True
    assert t.total_ticks is None
    assert summary(t).splitlines() == [
        "TOTAL: unknown (goal reached, but the trace has no segment_start record)",
        "  error engine_error at tick 171: late error",
    ]
