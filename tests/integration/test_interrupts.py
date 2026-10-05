"""Task 8.2: the map-pirate interrupt (segment.toml `interrupts`, C1 SPEEDRUN_INTERRUPTS).

From the 4th map entry on, a wandering pirate on the island map can force an
encounter on the road (room 49) when ego stands still next to him
(room-085-melee/local-202.txt [018A]-[01A2], global/script-114.txt). Its menu
always offers "Sorry to bother you. I'll be on my way." (room-049-road/local-200.txt
[0325]). With skips on, seed 292 of the current plan meets him while walking to
the forest fork, which then starts over (scanned with the full plan on seeds 1-300
with bridge v2: only 292 does; with v1, 164, 166 and 196 did, and v2's input
fidelity moved the route's timing by a few frames).
"""

import json

import pytest
from _pipeline import CompiledRoute, describe, run_route

pytestmark = [pytest.mark.integration, pytest.mark.requires_fd, pytest.mark.slow]

PIRATE_SEED = 292
ROAD, MAP = 49, 85
RESCAN = (
    "the route or its timing changed, so seed {seed} no longer meets the map pirate: find a seed that "
    "does (`speedrun measure part1 --seeds 1-300` with the interrupt removed fails on it with "
    "unexpected_choice) and update PIRATE_SEED"
)


def _records(trace, kind: str) -> list[dict]:
    return [r for r in trace.interrupts if r["type"] == kind]


def test_map_pirate_interrupt(full_route_compiled: CompiledRoute, tmp_path, home_scummvm_guard):
    out_dir = tmp_path / "run"
    trace = run_route(full_route_compiled, out_dir, seed=PIRATE_SEED).trace
    context = describe(trace, out_dir)
    assert trace.reached_goal and trace.errors == [], context

    starts, ends = _records(trace, "interrupt"), _records(trace, "interrupt_end")
    assert starts, RESCAN.format(seed=PIRATE_SEED) + "\n" + context
    assert len(starts) == len(ends)
    for start, end in zip(starts, ends):
        assert start["name"] == end["name"] == "map-pirate"
        assert start["room"] == ROAD and end["room"] == MAP  # global/script-114.txt [006E]-[0079]
        assert start["step"] == end["step"] and start["tick"] <= end["tick"]
        step = trace.steps[start["step"]]
        assert step.room_start == MAP
        if start["restart"]:
            # The map walk the encounter cut short started over and then ended normally.
            assert step.restarts >= 1 and step.finished, step

    choices = [line for line in (out_dir / "trace.jsonl").read_text().splitlines()
               if '"choice"' in line and '"interrupt":"map-pirate"' in line]  # fmt: skip
    assert len(choices) == len(starts) and all('"verb_id":124' in c for c in choices), choices

    # step_end.ticks counts from the step's first step_start, like its changes and the
    # trace reader's duration; ticks_since_restart counts from the last one (C5).
    records = [json.loads(line) for line in (out_dir / "trace.jsonl").read_text().splitlines()]
    step_starts: dict[int, list[int]] = {}
    for r in records:
        if r["type"] == "step_start":
            step_starts.setdefault(r["step"], []).append(r["tick"])
    restarted = []
    for end in (r for r in records if r["type"] == "step_end"):
        first, last = step_starts[end["step"]][0], step_starts[end["step"]][-1]
        assert end["ticks"] == end["tick"] - first, (end, step_starts[end["step"]])
        if len(step_starts[end["step"]]) > 1:
            restarted.append(end["step"])
            assert end["ticks_since_restart"] == end["tick"] - last, (end, step_starts[end["step"]])
        else:
            assert "ticks_since_restart" not in end, end
    assert restarted == sorted({s["step"] for s in starts if s["restart"]}), (restarted, starts)
    assert restarted, RESCAN.format(seed=PIRATE_SEED) + " (on a step it makes start over)"


def test_map_pirate_without_the_interrupt_is_unexpected_choice(full_route_compiled: CompiledRoute, tmp_path,
                                                                home_scummvm_guard):  # fmt: skip
    out_dir = tmp_path / "run"
    trace = run_route(full_route_compiled, out_dir, seed=PIRATE_SEED, interrupts=False).trace
    assert not trace.reached_goal, RESCAN.format(seed=PIRATE_SEED)
    (error,) = trace.errors
    assert error["code"] == "unexpected_choice", describe(trace, out_dir)
    assert "on my way" in error["message"]
