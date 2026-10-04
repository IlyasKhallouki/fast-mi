#!/usr/bin/env bash
# Reproducible ScummVM build: pinned submodule + patches/*.patch, out-of-tree
# in build/scummvm (SCUMM engine only).
#
# Usage: scripts/build-scummvm.sh [--no-reset] [-j N]
#
#   --no-reset  Skip the reset/clean/apply step and build whatever is in
#               third_party/scummvm right now (for bridge development).
#               Use scripts/export-patches.sh afterwards to save the edits.
#   -j N        Parallel make jobs (default: $JOBS, else nproc).
#
# Without --no-reset, ANY uncommitted edits inside third_party/scummvm are
# discarded: the submodule is reset to the pinned tag and patches re-applied.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCUMMVM="$ROOT/third_party/scummvm"
BUILD="$ROOT/build/scummvm"
PATCHES="$ROOT/patches"
SCUMMVM_TAG=v2026.3.0

CONFIGURE_FLAGS=(--disable-all-engines --enable-engine=scumm --disable-detection-full --enable-optimizations)

usage() { sed -n '2,13s/^# \{0,1\}//p' "${BASH_SOURCE[0]}"; }

RESET=1
JOBS="${JOBS:-}"
while (($#)); do
    case "$1" in
        --no-reset) RESET=0 ;;
        -j) [[ $# -ge 2 ]] || { echo "error: -j needs a value" >&2; exit 2; }
            JOBS="$2"; shift ;;
        -j*) JOBS="${1#-j}" ;;
        -h|--help) usage; exit 0 ;;
        *) echo "error: unknown argument: $1" >&2; usage >&2; exit 2 ;;
    esac
    shift
done
JOBS="${JOBS:-$(nproc)}"
[[ "$JOBS" =~ ^[1-9][0-9]*$ ]] || { echo "error: -j expects a positive integer, got '$JOBS'" >&2; exit 2; }

# --- 1. submodule ------------------------------------------------------------
if [[ ! -e "$SCUMMVM/.git" ]]; then
    echo "==> initialising submodule third_party/scummvm"
    git -C "$ROOT" submodule update --init --depth 1 third_party/scummvm
fi
# A depth-1 submodule fetch may not bring the tag ref along; fetch it if needed.
if ! git -C "$SCUMMVM" rev-parse -q --verify "refs/tags/$SCUMMVM_TAG^{commit}" >/dev/null; then
    echo "==> fetching tag $SCUMMVM_TAG"
    git -C "$SCUMMVM" fetch -q --depth 1 origin tag "$SCUMMVM_TAG"
fi

mkdir -p "$BUILD"

# --- 2. reset to the pinned tag and apply patches ------------------------------
if ((RESET)); then
    echo "==> resetting third_party/scummvm to $SCUMMVM_TAG"
    git -C "$SCUMMVM" reset -q --hard "$SCUMMVM_TAG"
    # -fd removes untracked files/dirs (e.g. engines/scumm/speedrun/ from a
    # previous apply); without -x, ignored files are left alone.
    git -C "$SCUMMVM" clean -fdq

    patch_files=()
    if [[ -d "$PATCHES" ]]; then
        mapfile -t patch_files < <(LC_ALL=C find "$PATCHES" -maxdepth 1 -type f -name '*.patch' | LC_ALL=C sort)
    fi

    if ((${#patch_files[@]} == 0)); then
        echo "no patches to apply (stock build)"
        patches_stamp=stock
    else
        for p in "${patch_files[@]}"; do
            echo "==> applying ${p#"$ROOT"/}"
            git -C "$SCUMMVM" apply --whitespace=nowarn "$p"
        done
        patches_stamp="$(cat "${patch_files[@]}" | sha256sum | cut -d' ' -f1)"
    fi
    printf '%s\n' "$patches_stamp" > "$BUILD/.patches-stamp"
else
    echo "==> --no-reset: building third_party/scummvm as-is"
fi

# --- 3. configure (only when flags changed) ----------------------------------
config_stamp="${CONFIGURE_FLAGS[*]}"
need_configure=1
if [[ -f "$BUILD/config.mk" ]]; then
    if [[ -f "$BUILD/.config-stamp" ]]; then
        if [[ "$(<"$BUILD/.config-stamp")" == "$config_stamp" ]]; then
            echo "==> configure flags unchanged, skipping configure"
            need_configure=0
        fi
    else
        # Build configured before this script existed: configure records its
        # arguments in config.mk as SAVED_CONFIGFLAGS. Reuse it on exact match.
        saved_flags="$(sed -n 's/^SAVED_CONFIGFLAGS[[:space:]]*:=[[:space:]]*//p' "$BUILD/config.mk" \
                       | sed 's/[[:space:]]*$//')"
        if [[ "$saved_flags" == "$config_stamp" ]]; then
            echo "==> existing config.mk has the same flags; writing .config-stamp, skipping configure"
            printf '%s\n' "$config_stamp" > "$BUILD/.config-stamp"
            need_configure=0
        fi
    fi
fi
if ((need_configure)); then
    echo "==> configuring: ${CONFIGURE_FLAGS[*]}"
    rm -f "$BUILD/.config-stamp"
    # Relative path on purpose: it becomes srcdir in the generated Makefile and
    # must stay the same so dependency paths (and thus the build) are reused.
    (cd "$BUILD" && ../../third_party/scummvm/configure "${CONFIGURE_FLAGS[@]}")
    printf '%s\n' "$config_stamp" > "$BUILD/.config-stamp"
fi

# --- 4. build ----------------------------------------------------------------
echo "==> make -j$JOBS"
make -C "$BUILD" -j"$JOBS"

# --- 5. version ----------------------------------------------------------------
# Always pass --config under out/, or ScummVM writes ~/.config/scummvm/scummvm.ini
# (and --logfile, so nothing can land in ~/.cache/scummvm/logs).
mkdir -p "$ROOT/out/scummvm"
version_out="$("$BUILD/scummvm" --config="$ROOT/out/scummvm/probe.ini" \
                --logfile="$ROOT/out/scummvm/build-version.log" --version)"
grep -m1 '^ScummVM' <<<"$version_out" || printf '%s\n' "$version_out"
