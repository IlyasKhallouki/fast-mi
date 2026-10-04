from pathlib import Path

import pytest

from speedrun import paths

BRIDGE_MARKER = "speedrun-bridge"


def _skip_reason(report) -> str:
    longrepr = report.longrepr
    if isinstance(longrepr, tuple) and len(longrepr) == 3:
        return str(longrepr[2]).removeprefix("Skipped: ")
    return str(longrepr)


def pytest_terminal_summary(terminalreporter, exitstatus, config):
    skipped = terminalreporter.stats.get("skipped", [])
    if not skipped:
        return
    terminalreporter.write_sep("!", red=True, bold=True)
    terminalreporter.write_line(
        f"!!! {len(skipped)} TESTS SKIPPED — skipped tests are information, not passes !!!",
        red=True,
        bold=True,
    )
    for report in skipped:
        nodeid = getattr(report, "nodeid", None) or "<unknown test>"
        terminalreporter.write_line(f"  {nodeid}: {_skip_reason(report)}", red=True)
    terminalreporter.write_sep("!", red=True, bold=True)


@pytest.fixture(scope="session")
def game_ready() -> Path:
    if not (paths.CLASSIC_DIR / "MONKEY1.000").exists():
        pytest.skip(
            "GAME DATA MISSING: game/classic/MONKEY1.000 not found — "
            "run `uv run speedrun extract` (integration test skipped)"
        )
    return paths.CLASSIC_DIR


@pytest.fixture(scope="session")
def fd_ready() -> Path:
    """The Fast Downward release build directory (``--build`` argument)."""
    # Imported here so a broken planner module fails only the tests that use it.
    from speedrun.planner import FD_BUILD, fd_available

    if not fd_available():
        pytest.skip("FAST DOWNWARD BUILD MISSING: run scripts/build-downward.sh")
    return FD_BUILD


@pytest.fixture(scope="session")
def stock_engine(game_ready) -> Path:
    """The ScummVM binary, patched or not. For tests that run unpatched ScummVM."""
    if not paths.SCUMMVM_BIN.exists():
        pytest.skip(
            "SCUMMVM BUILD MISSING: build/scummvm/scummvm not found — "
            "run scripts/build-scummvm.sh"
        )
    return paths.SCUMMVM_BIN


@pytest.fixture(scope="session")
def engine_ready(game_ready) -> Path:
    """The ScummVM binary, which must carry the speedrun bridge patch."""
    if not paths.SCUMMVM_BIN.exists():
        pytest.skip(
            "SCUMMVM BUILD MISSING: build/scummvm/scummvm not found — "
            "run scripts/build-scummvm.sh"
        )
    # The bridge sources embed BRIDGE_MARKER as a string constant, so a patched
    # binary contains it. Searching the bytes avoids running ScummVM at all.
    if BRIDGE_MARKER.encode() not in paths.SCUMMVM_BIN.read_bytes():
        pytest.skip(
            f"SCUMMVM BUILD IS NOT PATCHED: build/scummvm/scummvm lacks the "
            f"{BRIDGE_MARKER!r} marker — rebuild with scripts/build-scummvm.sh"
        )
    return paths.SCUMMVM_BIN
