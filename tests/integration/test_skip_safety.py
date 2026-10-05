"""Task 8.2 skip-safety harness: the full plan with and without skips, compared step by step.

For seeds 1-3 the current full plan runs twice: with text and cutscene skips (as every
measured run does) and without. Both write the whole state at every ``step_end``
(``SPEEDRUN_STEP_STATES``). The route-relevant state is compared at each step:

- every bit variable;
- the inventory, in order (inventory clicks depend on slot order);
- the owner of every object;
- ego's room;
- var 19 (``VAR_TIMER_NEXT``), which must be 6 in both runs (the logo speed glitch family).

A difference means a skipped override (or the shifted RNG stream) changed state. Each one
must be in ``EXPECTED``, with the reason it is harmless. A difference that is not listed
fails the test; the fix is a cited ``no_skip`` on the template (docs/plan.md C4) unless the
difference can be shown harmless and added here with its citation.

Variables other than var 19 are not compared: skips change how many frames pass, so timers,
the music timer, random draws and scratch variables differ throughout (docs/part1/skips.md
section 7.2).
"""

import json
from concurrent.futures import ThreadPoolExecutor
from fnmatch import fnmatch
from pathlib import Path

import pytest
from _pipeline import CompiledRoute, describe, run_route

pytestmark = [pytest.mark.integration, pytest.mark.requires_fd, pytest.mark.slow]

SEEDS = (1, 2, 3)
TIMER_NEXT = 6  # var 19: global/script-001.txt [07B3], room-010-logo/local-204.txt [0097]

# (field, key) -> (the action, as an fnmatch pattern, where the difference may first
# appear; or None if a random draw decides when; why it is harmless).
EXPECTED = {
    ("bit", 561): (
        "walk-out-of-bar-from-*-meanwhile",
        "docs/part1/skips.md section 4.4 (A7): set only by room-070-hellcliff/entry.txt [0000], which the "
        "override of global/script-120.txt [000E] -> [052D] never loads; no reader in data/scripts",
    ),
    ("owner", 630): (
        "enter-idol-room",
        "docs/part1/skips.md section 4.4 (A38): the vase stays outside the inventory on both paths "
        "(14 on the normal path, room-053-foyer/local-210.txt [006E]; 15 when the override "
        "[0007] -> [042F] skips local-206); its readers are off-route",
    ),
    ("bit", 324): (
        None,
        "RNG drift, not an override: the storekeeper is away on 1 store entry in 4 "
        "(room-030-store/entry.txt [002B] getRandomNr(3)), and Bit[324] records that a returning "
        "storekeeper caught ego (room-030-store/local-204.txt [02F4]). Skips shift the RNG stream "
        "(docs/part1/skips.md section 7.2). Its readers only pick a line: local-200.txt [017D], "
        "local-204.txt [02EF], local-212.txt [00ED]",
    ),
}


def _diff(a: dict, b: dict) -> dict:
    """(field, key) -> (with skips, without skips) for every compared difference."""
    out: dict = {}
    bits_a, bits_b = set(a["bits_set"]), set(b["bits_set"])
    for bit in sorted(bits_a ^ bits_b):
        out[("bit", bit)] = (int(bit in bits_a), int(bit in bits_b))
    if a["inventory"] != b["inventory"]:
        out[("inventory", None)] = (a["inventory"], b["inventory"])
    for obj, owner in a["owners"].items():
        if owner != b["owners"][obj]:
            out[("owner", int(obj))] = (owner, b["owners"][obj])
    if a["room"] != b["room"]:
        out[("room", None)] = (a["room"], b["room"])
    if a["vars"][19] != b["vars"][19]:
        out[("var", 19)] = (a["vars"][19], b["vars"][19])
    return out


@pytest.fixture(scope="module")
def runs(full_route_compiled: CompiledRoute, tmp_path_factory, home_scummvm_guard_factory) -> dict:
    """(seed, skips) -> run dir, every run with per-step state dumps."""
    base = tmp_path_factory.mktemp("skip-safety")
    jobs = [(seed, skips) for seed in SEEDS for skips in (True, False)]

    def run(job):
        seed, skips = job
        out_dir = base / f"seed-{seed}-{'skips' if skips else 'no-skips'}"
        trace = run_route(full_route_compiled, out_dir, seed, skips=skips, step_states=True).trace
        assert trace.reached_goal and trace.errors == [], describe(trace, out_dir)
        return out_dir

    with home_scummvm_guard_factory(), ThreadPoolExecutor(max_workers=len(jobs)) as pool:
        return dict(zip(jobs, pool.map(run, jobs)))


def _state(run_dir: Path, step: int) -> dict | None:
    path = run_dir / f"state-step-{step:03d}.json"
    return json.loads(path.read_text(encoding="ascii")) if path.is_file() else None


def test_skips_change_no_route_state(runs, full_route_compiled: CompiledRoute):
    steps = full_route_compiled.steps
    report: list[str] = []
    unexpected: list[str] = []
    for seed in SEEDS:
        previous: dict = {}
        compared = 0
        for k, step in enumerate(steps):
            a, b = _state(runs[(seed, True)], k), _state(runs[(seed, False)], k)
            if a is None or b is None:
                # Only the last step may lack a step_end: the goal fires during it (C5).
                assert k == len(steps) - 1 and a is None and b is None, (seed, k, a is None, b is None)
                continue
            compared += 1
            assert a["vars"][19] == b["vars"][19] == TIMER_NEXT, (seed, k, a["vars"][19], b["vars"][19])
            diffs = _diff(a, b)
            # Report each difference where it appears, changes or goes away, not at every later step.
            for item, values in diffs.items():
                if previous.get(item) == values:
                    continue
                field, key = item
                what = f"{field}{'' if key is None else ' ' + str(key)}"
                report.append(f"seed {seed} step {k} {step['action']}: {what} with skips {values[0]}, "
                              f"without {values[1]}")  # fmt: skip
                expected = EXPECTED.get(item)
                if expected is None:
                    unexpected.append(f"seed {seed}: {what} differs from step {k} ({step['action']})")
                elif item not in previous and expected[0] is not None and not fnmatch(step["action"], expected[0]):
                    unexpected.append(f"seed {seed}: {what} first differs at {step['action']!r}, "
                                      f"expected at {expected[0]!r}")  # fmt: skip
            for item in previous.keys() - diffs.keys():
                report.append(f"seed {seed} step {k} {step['action']}: {item} equal again")
            previous = diffs
        assert compared >= len(steps) - 1, (seed, compared)
    print("\n".join(["skip-safety differences (with skips vs without):", *report] if report else ["no differences"]))
    assert unexpected == [], "\n".join(unexpected + ["", *report])
