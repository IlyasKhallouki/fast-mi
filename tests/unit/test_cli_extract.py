"""The Phase 7 commands ``extract-check``, ``extract-merge`` and ``pddl-diff``, and ``scripts/check-citations.py``.

Every path is redirected into ``tmp_path``: the commands never read or write the
real ``out/``, ``docs/``, ``pddl/`` or ``data/`` trees here.
"""

import json
import os
import subprocess
import sys

import pytest
from _extract_toy import FRAGMENTS, HAND_DOMAIN, OBJECTS, YARD, action, make_hand_segment, make_scripts, state_dump

from speedrun import paths
from speedrun.citations import parse_sexp
from speedrun.cli import main

SCRIPT = paths.SCRIPTS_DIR / "check-citations.py"


@pytest.fixture
def env(tmp_path, monkeypatch):
    for name, sub in (
        ("OUT_DIR", "out"),
        ("PLANS_DIR", "out/plans"),
        ("RUNS_DIR", "out/runs"),
        ("PDDL_DIR", "pddl"),
        ("DATA_DIR", "data"),
        ("DOCS_DIR", "docs"),
    ):
        monkeypatch.setattr(paths, name, tmp_path / sub)
    make_scripts(tmp_path / "data" / "scripts")
    make_hand_segment(tmp_path / "pddl", "toy")
    frag_dir = tmp_path / "out" / "extract" / "toy"
    frag_dir.mkdir(parents=True)
    for name, text in FRAGMENTS.items():
        (frag_dir / name).write_text(text, encoding="utf-8")
    (tmp_path / "out" / "objects.json").write_text(json.dumps(OBJECTS))
    return tmp_path


def _write_state(env, run: str, **overrides) -> None:
    run_dir = env / "out" / "runs" / run
    run_dir.mkdir(parents=True)
    (run_dir / "state-start.json").write_text(json.dumps(state_dump(**overrides)))


def test_help_lists_the_extraction_commands(capsys):
    with pytest.raises(SystemExit):
        main(["--help"])
    out = capsys.readouterr().out
    for name in ("extract-check", "extract-merge", "pddl-diff"):
        assert name in out


# --- extract-check -----------------------------------------------------------------------


def test_extract_check_passes_valid_fragments(env, capsys):
    assert main(["extract-check", "toy"]) == 0
    out = capsys.readouterr().out
    assert "2 fragment(s), 8 action(s), 0 issue(s)" in out


def test_extract_check_lists_issues_and_fails(env, capsys):
    (env / "out" / "extract" / "toy" / "bad.pddl").write_text(action("uncited", src=()))
    assert main(["extract-check", "toy"]) == 1
    out = capsys.readouterr().out
    assert "bad.pddl" in out and "uncited" in out and "no-src" in out
    assert "3 fragment(s), 9 action(s), 1 issue(s)" in out


def test_extract_check_ignores_the_merged_model(env, capsys):
    (env / "out" / "extract" / "toy" / "domain.pddl").write_text(HAND_DOMAIN)
    assert main(["extract-check", "toy"]) == 0


def test_extract_check_without_fragments_fails(env, capsys):
    assert main(["extract-check", "nothing"]) == 1
    assert "no extraction fragments" in capsys.readouterr().err


# --- extract-merge -----------------------------------------------------------------------


def test_extract_merge_writes_the_model_and_the_rejected_list(env, capsys):
    frag_dir = env / "out" / "extract" / "toy"
    (frag_dir / "bad.pddl").write_text(action("uncited", src=()) + "\n" + action("fine-door"))
    state = env / "state.json"
    state.write_text(json.dumps(state_dump()))
    assert main(["extract-merge", "toy", "--state", str(state)]) == 0

    domain = (frag_dir / "domain.pddl").read_text()
    problem = (frag_dir / "problem.pddl").read_text()
    (dtree,) = parse_sexp(domain)
    names = [i[1] for i in dtree if isinstance(i, list) and i and i[0] == ":action"]
    assert "fine-door" in names and "uncited" not in names and "take-chest" in names
    assert "(:domain toy-extracted)" in problem
    assert "(:goal (and (bit-85) (bit-86)))" in problem  # from segment.toml

    rejected = json.loads((frag_dir / "rejected.json").read_text())
    assert [(r["fragment"], r["action"]) for r in rejected] == [("bad.pddl", "uncited")]
    assert rejected[0]["issues"][0]["code"] == "no-src"
    out = capsys.readouterr().out
    assert "uncited" in out and str(state) in out


def test_extract_merge_twice_gives_the_same_model(env):
    state = env / "state.json"
    state.write_text(json.dumps(state_dump()))
    assert main(["extract-merge", "toy", "--state", str(state)]) == 0
    first = (env / "out" / "extract" / "toy" / "domain.pddl").read_text()
    assert main(["extract-merge", "toy", "--state", str(state)]) == 0  # its own output is not a fragment
    assert (env / "out" / "extract" / "toy" / "domain.pddl").read_text() == first


def test_extract_merge_defaults_to_the_newest_measured_state_dump(env, capsys):
    _write_state(env, "20261001T000000Z-run", room=91)
    _write_state(env, "20261002T000000Z-run", room=90)
    _write_state(env, "20261003T000000Z-run", room=92, boot_param=3)  # a debug start: not a real start state
    assert main(["extract-merge", "toy"]) == 0
    problem = (env / "out" / "extract" / "toy" / "problem.pddl").read_text()
    assert "(at-r90)" in problem and "(at-r92)" not in problem.split("(:init")[1].split("(:goal")[0]
    assert "20261002T000000Z-run" in capsys.readouterr().out


def test_extract_merge_without_a_state_dump_fails(env, capsys):
    assert main(["extract-merge", "toy"]) == 1
    assert "--state" in capsys.readouterr().err


def test_extract_merge_with_everything_rejected_fails(env, capsys):
    frag_dir = env / "out" / "extract" / "toy"
    for p in frag_dir.glob("*.pddl"):
        p.unlink()
    (frag_dir / "bad.pddl").write_text(action("uncited", src=()))
    state = env / "state.json"
    state.write_text(json.dumps(state_dump()))
    assert main(["extract-merge", "toy", "--state", str(state)]) == 1
    assert "rejected" in capsys.readouterr().err
    assert json.loads((frag_dir / "rejected.json").read_text())[0]["action"] == "uncited"


# --- pddl-diff ------------------------------------------------------------------------------


def test_pddl_diff_writes_the_report(env, capsys):
    (env / "out" / "extract" / "toy" / "bad.pddl").write_text(action("uncited", src=()))
    assert main(["pddl-diff", "toy"]) == 0
    report = (env / "docs" / "extraction-diff.md").read_text()
    assert report.startswith("# Extraction diff: toy")
    assert "`walk-through-door`" in report and "`walk-yard-to-hall`" in report
    assert "1 extracted action(s) rejected" in report
    assert str(env / "docs" / "extraction-diff.md") in capsys.readouterr().out


def test_pddl_diff_out_option(env):
    out = env / "elsewhere.md"
    assert main(["pddl-diff", "toy", "--out", str(out)]) == 0
    assert out.read_text().startswith("# Extraction diff: toy")


def test_pddl_diff_falls_back_to_the_script_index(env):
    (env / "out" / "objects.json").unlink()
    index = {
        "objects": {
            str(o["id"]): {"name": o["name"], "room": room["room"]} for room in OBJECTS["rooms"] for o in room["objects"]
        },
        "verbs": {str(v["id"]): {"name": v["name"]} for v in OBJECTS["verbs"]},
    }
    (env / "data" / "scripts" / "index.json").write_text(json.dumps(index))
    assert main(["pddl-diff", "toy"]) == 0
    assert "`walk-yard-to-hall`" in (env / "docs" / "extraction-diff.md").read_text()


def test_pddl_diff_without_any_object_index_fails(env, capsys):
    (env / "out" / "objects.json").unlink()
    assert main(["pddl-diff", "toy"]) == 1
    assert "objects.json" in capsys.readouterr().err


# --- scripts/check-citations.py ------------------------------------------------------------


def _script(*args, cwd):
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    return subprocess.run([sys.executable, str(SCRIPT), *map(str, args)], capture_output=True, text=True,
                          cwd=cwd, env=env, timeout=60, check=False)  # fmt: skip


def test_check_citations_script_accepts_valid_fragments(tmp_path):
    scripts = make_scripts(tmp_path / "scripts")
    (tmp_path / "yard.pddl").write_text(YARD)
    result = _script("--scripts-dir", scripts, tmp_path / "yard.pddl", cwd=tmp_path)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "1 file(s), 3 action(s), 0 issue(s)" in result.stdout


def test_check_citations_script_lists_issues(tmp_path):
    scripts = make_scripts(tmp_path / "scripts")
    bad = "; src: data/scripts/room-090-yard/obj-0901-door.txt [0011] — wrong offset"
    (tmp_path / "a.pddl").write_text(action("a", src=(bad,)))
    (tmp_path / "b.pddl").write_text(action("a"))
    result = _script("--scripts-dir", scripts, tmp_path / "a.pddl", tmp_path / "b.pddl", cwd=tmp_path)
    assert result.returncode == 1
    assert "bad-offset" in result.stdout and "duplicate-name" in result.stdout
    assert "a.pddl" in result.stdout


def test_check_citations_script_citations_only(tmp_path):
    scripts = make_scripts(tmp_path / "scripts")
    (tmp_path / "domain.pddl").write_text(HAND_DOMAIN)
    full = _script("--scripts-dir", scripts, tmp_path / "domain.pddl", cwd=tmp_path)
    assert full.returncode == 1
    only = _script("--citations-only", "--scripts-dir", scripts, tmp_path / "domain.pddl", cwd=tmp_path)
    assert only.returncode == 0, only.stdout + only.stderr
    assert "8 action(s), 0 issue(s)" in only.stdout


def test_check_citations_script_missing_file(tmp_path):
    result = _script(tmp_path / "nope.pddl", cwd=tmp_path)
    assert result.returncode == 2
    assert "nope.pddl" in result.stderr
