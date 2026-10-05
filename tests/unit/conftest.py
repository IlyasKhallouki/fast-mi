"""Unit-test isolation: the CLI must not read the real ScummVM build.

``speedrun.cli`` checks the time plan's measured bridge against the bridge
compiled into ``build/scummvm/scummvm``. Unit tests use synthetic traces with
their own bridge marker, so they would otherwise depend on whichever binary is
built. By default the built bridge is "unknown" (None), which skips that
check; tests about the check set ``cli.bridge_version`` themselves.
"""

import pytest


@pytest.fixture(autouse=True)
def _no_real_bridge(monkeypatch):
    monkeypatch.setattr("speedrun.cli.bridge_version", lambda: None)
