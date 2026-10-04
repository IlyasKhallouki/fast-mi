"""`speedrun dump-objects` end to end on the patched engine (Task 4.3 acceptance)."""

import json

import pytest

from speedrun import cli, paths
from speedrun.trace import load_trace


@pytest.mark.integration
def test_cli_dump_objects(engine_ready, tmp_path, monkeypatch, home_scummvm_guard, capsys):
    # The bridge writes the literal end reason "dump_done" once it has the
    # object dump (Task 1.2); until then the binary cannot pass this test.
    if b"dump_done" not in engine_ready.read_bytes():
        pytest.skip(
            "BRIDGE HAS NO OBJECT DUMP YET: build/scummvm/scummvm lacks the 'dump_done' "
            "end reason (Task 1.2) — rebuild with scripts/build-scummvm.sh"
        )
    out = tmp_path / "out"
    monkeypatch.setattr(paths, "OUT_DIR", out)
    monkeypatch.setattr(paths, "RUNS_DIR", out / "runs")
    monkeypatch.setattr(paths, "PLANS_DIR", out / "plans")

    rc = cli.main(["dump-objects"])
    output = capsys.readouterr()
    assert rc == 0, output.out + output.err

    (run_dir,) = (out / "runs").iterdir()
    trace = load_trace(run_dir / "trace.jsonl")
    assert trace.end["reason"] == "dump_done", trace.end
    assert trace.errors == []

    dump = json.loads((out / "objects.json").read_text(encoding="utf-8"))
    assert dump == json.loads((run_dir / "objects.json").read_text(encoding="utf-8"))
    assert len(dump["rooms"]) >= 80
    verbs = {v["name"].strip("@ ").casefold() for v in dump["verbs"]}
    for name in ("open", "pick up", "walk to"):
        assert name in verbs, sorted(verbs)
    for room in dump["rooms"]:
        ids = [o["id"] for o in room["objects"]]
        assert len(ids) == len(set(ids)), f"room {room['room']} has duplicate object ids"
    assert f"{len(dump['rooms'])} rooms" in output.out
