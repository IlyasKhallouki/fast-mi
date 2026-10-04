"""Canonical filesystem locations. Every other module imports paths from here."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

GAME_DIR = ROOT / "game"
CLASSIC_DIR = GAME_DIR / "classic"

BUILD_DIR = ROOT / "build"
SCUMMVM_BIN = BUILD_DIR / "scummvm" / "scummvm"

OUT_DIR = ROOT / "out"
PLANS_DIR = OUT_DIR / "plans"
RUNS_DIR = OUT_DIR / "runs"

PDDL_DIR = ROOT / "pddl"
DOCS_DIR = ROOT / "docs"
DOWNWARD_DIR = ROOT / "third_party" / "downward"
SCRIPTS_DIR = ROOT / "scripts"
DATA_DIR = ROOT / "data"
