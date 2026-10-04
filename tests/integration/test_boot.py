"""Boots the stock (or patched) ScummVM headless and checks it stays out of $HOME."""

from pathlib import Path

import pytest

from speedrun.engine import EngineConfig, run_engine

MI1_MAC_MD5 = "2ccd8891ce4d3f1a334d21bff6a88ca2"


def _home_scummvm_dirs() -> list[Path]:
    home = Path.home()
    return [
        home / ".config" / "scummvm",
        home / ".local" / "share" / "scummvm",
        home / ".cache" / "scummvm",
    ]


def _snapshot(root: Path):
    """None if absent, else every entry under root with its mtime."""
    if not root.exists():
        return None
    entries = [(".", root.stat().st_mtime_ns)]
    for p in sorted(root.rglob("*")):
        entries.append((str(p.relative_to(root)), p.lstat().st_mtime_ns))
    return entries


@pytest.mark.integration
def test_stock_boot_headless(stock_engine, tmp_path):
    before = {d: _snapshot(d) for d in _home_scummvm_dirs()}

    cfg = EngineConfig(out_dir=tmp_path / "run", timeout_s=20, extra_args=["--debuglevel=1"])
    result = run_engine(cfg)

    log = result.log_path.read_text(errors="replace")
    assert result.log_path == tmp_path / "run" / "stdout.log"
    assert result.timed_out, f"ScummVM exited early (rc={result.returncode}):\n{log}"
    assert "variant Mac" in log, log
    assert f"Using MD5 '{MI1_MAC_MD5}'" in log, log
    assert "Segmentation fault" not in log, log
    assert "ERROR:" not in log, log

    after = {d: _snapshot(d) for d in _home_scummvm_dirs()}
    for d in _home_scummvm_dirs():
        if before[d] is None:
            assert after[d] is None, f"ScummVM created {d} in the user's home"
        else:
            assert after[d] == before[d], f"ScummVM modified {d} in the user's home"
