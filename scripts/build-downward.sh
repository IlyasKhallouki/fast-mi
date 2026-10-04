#!/usr/bin/env bash
# Build Fast Downward (submodule third_party/downward, release config) out of
# tree in build/downward/release, with the exact commands from
# docs/research/fast-downward.md. Idempotent: configure runs only when there is
# no CMakeCache.txt yet, and the build step is incremental, so a second run is
# a quick no-op. Prints the search binary's path when done.
#
# Usage: scripts/build-downward.sh        (JOBS=N to change the default -j 4)
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOWNWARD="$ROOT/third_party/downward"
BUILD="$ROOT/build/downward/release"
BIN="$BUILD/bin/downward"
JOBS="${JOBS:-4}"
[[ "$JOBS" =~ ^[1-9][0-9]*$ ]] || { echo "error: JOBS must be a positive integer, got '$JOBS'" >&2; exit 2; }

if [[ ! -f "$DOWNWARD/src/CMakeLists.txt" ]]; then
    echo "error: $DOWNWARD/src/CMakeLists.txt not found; run: git submodule update --init third_party/downward" >&2
    exit 1
fi

# CMake shells out to `git log` / `git diff-index` in the submodule to stamp the revision.
cd "$DOWNWARD"

if [[ ! -f "$BUILD/CMakeCache.txt" ]]; then
    echo "==> configuring $BUILD"
    cmake -S "$DOWNWARD/src" -B "$BUILD" -G "Unix Makefiles" -DCMAKE_BUILD_TYPE=Release
fi

echo "==> building $BUILD (-j $JOBS)"
cmake --build "$BUILD" -j "$JOBS"

[[ -x "$BIN" ]] || { echo "error: build finished but $BIN is missing" >&2; exit 1; }
echo "$BIN"
