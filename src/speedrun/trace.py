"""Parse the bridge's ``trace.jsonl`` (contract C5) and report on it.

``load_trace`` groups the records into a ``Trace``: the ``boot``,
``segment_start``, ``goal`` and ``end`` records, the ``error``, ``stall`` and
``interrupt``/``interrupt_end`` records, and one ``StepRecord`` per plan step
(``step_start`` + ``step_end``, plus that step's ``choice`` and ``click``
records). A step an interrupt made start over has a second ``step_start``; the
first one counts. Unknown record types and
unknown fields are ignored, so the bridge can grow new records without
breaking old readers.

Ticks are absolute from boot (C2). Reported times are relative to the
segment start's ``tick0``; steps the plan player ran before the segment
started (e.g. answering an opening dialogue) get negative relative ticks.

The bridge writes ASCII JSON in which every game-text byte >= 0x80 is a
``\\u00XX`` escape of that byte. Choice texts and error messages are decoded
with the shared game-text decoder, ``speedrun.text.decode_game_text`` (C5).
"""

import json
from dataclasses import dataclass, field
from pathlib import Path

from speedrun.text import decode_game_text

TICKS_PER_SECOND = 60

# Inventory and bit lists longer than this are cut short in the changes column.
_MAX_LISTED = 6

CHANGES_LEGEND = (
    "changes: +inv/-inv = object ids added to/removed from the inventory; "
    "bits = bit variables that changed; vars = how many global vars changed; "
    "room = room transition"
)


class TraceError(Exception):
    """The trace file is missing, empty or truncated, or a line is not a C5 record."""


@dataclass
class StepRecord:
    """One plan step, assembled from its ``step_start``/``step_end``/``choice``/``click`` records."""

    index: int
    action: str | None = None
    room_start: int | None = None
    room_end: int | None = None  # None while the step has no step_end (it failed or the run stopped)
    start_tick: int | None = None
    end_tick: int | None = None
    changes: dict = field(default_factory=dict)
    choices: list[str] = field(default_factory=list)  # decoded choice texts, in order (the plan's own)
    clicks: list[int] = field(default_factory=list)  # clicked verb ids, in order
    # How often an interrupt made the step start over. ``start_tick`` stays the first
    # start, so the interrupt counts towards the step.
    restarts: int = 0

    @property
    def duration(self) -> int | None:
        if self.start_tick is None or self.end_tick is None:
            return None
        return self.end_tick - self.start_tick

    @property
    def finished(self) -> bool:
        return self.end_tick is not None


@dataclass
class Trace:
    boot: dict | None = None
    segment_start: dict | None = None
    steps: list[StepRecord] = field(default_factory=list)
    goal: dict | None = None
    errors: list[dict] = field(default_factory=list)
    stalls: list[dict] = field(default_factory=list)
    interrupts: list[dict] = field(default_factory=list)  # interrupt and interrupt_end records, in order
    end: dict | None = None

    @property
    def tick0(self) -> int | None:
        """The segment start tick, or None if the segment never started."""
        if self.segment_start is None:
            return None
        return self.segment_start.get("tick0", self.segment_start.get("tick"))

    @property
    def reached_goal(self) -> bool:
        return self.goal is not None

    @property
    def total_ticks(self) -> int | None:
        """Ticks from segment start to goal, or None without both records."""
        if self.goal is None or self.tick0 is None:
            return None
        return self.goal["tick"] - self.tick0


def _read_records(path: Path) -> list[dict]:
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        raise TraceError(f"no trace at {path} (the engine did not write one)") from None
    except (OSError, UnicodeDecodeError) as e:
        raise TraceError(f"cannot read trace {path}: {e}") from e

    records = []
    for lineno, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError as e:
            raise TraceError(
                f"{path} line {lineno} is not valid JSON ({e.msg}); the trace looks truncated "
                "(was the engine killed mid-write?)"
            ) from None
        if not isinstance(record, dict) or not isinstance(record.get("type"), str):
            raise TraceError(f"{path} line {lineno} is not a trace record (an object with a 'type'): {line!r}")
        records.append(record)
    if not records:
        raise TraceError(f"trace {path} is empty (the engine wrote no records)")
    return records


def load_trace(path: Path) -> Trace:
    """Read ``trace.jsonl`` into a ``Trace``. Raises ``TraceError`` if it is missing, empty or truncated."""
    path = Path(path)
    trace = Trace()
    steps: dict[int, StepRecord] = {}

    for r in _read_records(path):
        kind = r["type"]
        if kind in _STEP_RECORDS:
            index = r.get("step")
            if isinstance(index, int):
                _apply_step_record(steps.setdefault(index, StepRecord(index=index)), kind, r)
        elif kind == "boot" and trace.boot is None:
            trace.boot = r
        elif kind == "segment_start" and trace.segment_start is None:
            trace.segment_start = r
        elif kind == "goal" and trace.goal is None:
            trace.goal = r
        elif kind == "end":
            trace.end = r
        elif kind == "error":
            trace.errors.append({**r, "message": decode_game_text(r.get("message"))})
        elif kind == "stall":
            trace.stalls.append(r)
        elif kind in ("interrupt", "interrupt_end"):
            trace.interrupts.append(r)
        # Anything else is a record type this reader does not know: ignore it.

    trace.steps = [steps[i] for i in sorted(steps)]
    return trace


_STEP_RECORDS = frozenset({"step_start", "step_end", "choice", "click"})


def _apply_step_record(s: StepRecord, kind: str, r: dict) -> None:
    if kind == "step_start":
        if s.start_tick is not None:  # an interrupt made the step start over
            s.restarts += 1
            return
        s.action = r.get("action")
        s.room_start = r.get("room")
        s.start_tick = r.get("tick")
    elif kind == "step_end":
        s.end_tick = r.get("tick")
        s.changes = r.get("changes") or {}
        room = r.get("room")
        if room is None:  # fall back to the end of the changes' [from, to] room pair
            pair = s.changes.get("room")
            room = pair[1] if isinstance(pair, list) and len(pair) == 2 else None
        s.room_end = room
    elif kind == "choice":
        if "interrupt" not in r:
            s.choices.append(decode_game_text(r.get("text")))
    else:  # click
        s.clicks.append(r.get("verb_id"))


def format_ticks(ticks: int) -> str:
    """``M:SS.ss`` for a tick count at 60 Hz, rounded to the nearest centisecond."""
    sign = "-" if ticks < 0 else ""
    # Integer centiseconds (ticks * 100 / 60), so rounding can never print ":60.00".
    q, r = divmod(abs(ticks) * 100, TICKS_PER_SECOND)
    centis = q + (1 if 2 * r >= TICKS_PER_SECOND else 0)
    minutes, rest = divmod(centis, 6000)
    seconds, hundredths = divmod(rest, 100)
    return f"{sign}{minutes}:{seconds:02d}.{hundredths:02d}"


def _ids(keys) -> list:
    """Sort ids numerically where possible (JSON object keys are strings)."""
    return sorted(keys, key=lambda k: (0, int(k), "") if str(k).lstrip("-").isdigit() else (1, 0, str(k)))


def _listing(ids: list) -> str:
    shown = ",".join(str(i) for i in ids[:_MAX_LISTED])
    if len(ids) > _MAX_LISTED:
        shown += f" (+{len(ids) - _MAX_LISTED} more)"
    return shown


def format_changes(changes: dict | None) -> str:
    """Compact summary of a ``step_end`` ``changes`` object, e.g. ``+inv 567, bits 85, vars 3, room 28→41``.

    Inventory and bits list ids; vars give a count (see ``CHANGES_LEGEND``).
    Missing or null keys are treated as "no change".
    """
    if not changes:
        return ""
    parts = []
    inventory = changes.get("inventory") or {}
    added, removed = inventory.get("added") or [], inventory.get("removed") or []
    if added:
        parts.append(f"+inv {_listing(list(added))}")
    if removed:
        parts.append(f"-inv {_listing(list(removed))}")
    bits = changes.get("bits") or {}
    if bits:
        parts.append(f"bits {_listing(_ids(bits))}")
    variables = changes.get("vars") or {}
    if variables:
        parts.append(f"vars {len(variables)}")
    room = changes.get("room")
    if isinstance(room, list) and len(room) == 2 and room[0] != room[1]:
        parts.append(f"room {room[0]}→{room[1]}")
    return ", ".join(parts)


def _cell(value: object) -> str:
    return "?" if value is None else str(value)


def _goal_closed_step(trace: Trace) -> StepRecord | None:
    """The last step, if it has no ``step_end`` because the goal fired during it."""
    if trace.goal is None or not trace.steps:
        return None
    last, goal_tick = trace.steps[-1], trace.goal.get("tick")
    if last.finished or not isinstance(last.start_tick, int) or not isinstance(goal_tick, int):
        return None
    return last if goal_tick >= last.start_tick else None


def format_table(trace: Trace) -> str:
    """Per-step table: ``#``, ``action``, ``room``, ``start``, ``end``, ``ticks``, ``changes``.

    ``start``/``end`` are relative to ``tick0`` (negative before the segment
    start), or absolute from boot if the segment never started.

    A goal that fires during the last step leaves that step without a
    ``step_end`` (C5 "Goal mid-step"): its row ends at the goal tick, and its
    changes column reads ``goal``.
    """
    tick0 = trace.tick0
    base = 0 if tick0 is None else tick0
    notes = []
    if tick0 is None:
        notes.append("(no segment_start record: start/end are absolute ticks from boot)")
    if not trace.steps:
        return "\n".join([*notes, "(no steps in trace)"])

    goal_step = _goal_closed_step(trace)
    header = ["#", "action", "room", "start", "end", "ticks", "changes"]
    rows = []
    for s in trace.steps:
        start = None if s.start_tick is None else s.start_tick - base
        if s is goal_step:
            end_tick, duration, changes = trace.goal["tick"], trace.goal["tick"] - s.start_tick, "goal"
        else:
            end_tick, duration = s.end_tick, s.duration
            changes = format_changes(s.changes) if s.finished else "(no step_end: step did not finish)"
        end = None if end_tick is None else end_tick - base
        rows.append([str(s.index), _cell(s.action), _cell(s.room_start), _cell(start), _cell(end),
                     _cell(duration), changes])  # fmt: skip

    widths = [max(len(r[i]) for r in [header, *rows]) for i in range(len(header) - 1)]
    left = {1}  # action is left-aligned, numbers right-aligned; changes is last and unpadded

    def line(cells: list[str]) -> str:
        out = [c.ljust(w) if i in left else c.rjust(w) for i, (c, w) in enumerate(zip(cells, widths))]
        return "  ".join([*out, cells[-1]]).rstrip()

    return "\n".join([*notes, line(header), *(line(r) for r in rows), CHANGES_LEGEND])


def format_error(err: dict) -> str:
    """One indented line for an `error` record: code, tick, step and decoded message."""
    where = f" (step {err['step']})" if isinstance(err.get("step"), int) else ""
    message = err.get("message")
    text = f": {message}" if message else ""
    return f"  error {err.get('code', '?')} at tick {_cell(err.get('tick'))}{where}{text}"


def _stall_line(stall: dict) -> str:
    slot = f" (slot {stall['slot']})" if "slot" in stall else ""
    return f"  stall at tick {_cell(stall.get('tick'))}: {stall.get('reason', '?')}{slot}"


def summary(trace: Trace) -> str:
    """``TOTAL: N ticks (M:SS.ss at 60 Hz)``, or ``NO GOAL: end reason X`` with errors and stalls."""
    total = trace.total_ticks
    if total is not None:
        lines = [f"TOTAL: {total} ticks ({format_ticks(total)} at 60 Hz)"]
    elif trace.reached_goal:
        lines = ["TOTAL: unknown (goal reached, but the trace has no segment_start record)"]
    else:
        if trace.end is None:
            reason = "unknown (no end record: the engine was killed or crashed)"
        else:
            reason = trace.end.get("reason", "?")
        lines = [f"NO GOAL: end reason {reason}"]
        lines += [_stall_line(s) for s in trace.stalls]
    lines += [format_error(e) for e in trace.errors]
    return "\n".join(lines)
