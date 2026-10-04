"""Boots ScummVM headless (bridge active, since run_engine sets SPEEDRUN_OUT) and
checks it detects Mac MI1 and stays out of $HOME."""

import pytest

from speedrun.engine import EngineConfig, run_engine

MI1_MAC_MD5 = "2ccd8891ce4d3f1a334d21bff6a88ca2"


@pytest.mark.integration
def test_boot_headless_detects_mac_monkey(stock_engine, tmp_path, home_scummvm_guard):
    cfg = EngineConfig(out_dir=tmp_path / "run", timeout_s=20, extra_args=["--debuglevel=1"])
    result = run_engine(cfg)

    log = result.log_path.read_text(errors="replace")
    assert result.log_path == tmp_path / "run" / "stdout.log"
    assert result.timed_out, f"ScummVM exited early (rc={result.returncode}):\n{log}"
    assert "variant Mac" in log, log
    assert f"Using MD5 '{MI1_MAC_MD5}'" in log, log
    assert "Segmentation fault" not in log, log
    assert "ERROR:" not in log, log
