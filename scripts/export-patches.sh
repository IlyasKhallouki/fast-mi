#!/usr/bin/env bash
# Export the current edits in third_party/scummvm (relative to the pinned tag)
# to patches/0001-scumm-add-speedrun-bridge.patch.
#
# Pure export: commits nothing in the submodule or the parent repo. New files
# under engines/scumm/speedrun/ are marked intent-to-add so they show up in
# the diff; the next scripts/build-scummvm.sh (without --no-reset) resets that.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCUMMVM="$ROOT/third_party/scummvm"
PATCHES="$ROOT/patches"
SCUMMVM_TAG=v2026.3.0
PATCH_NAME=0001-scumm-add-speedrun-bridge.patch
PATCH="$PATCHES/$PATCH_NAME"

mkdir -p "$PATCHES"

if [[ -d "$SCUMMVM/engines/scumm/speedrun" ]]; then
    git -C "$SCUMMVM" add -N engines/scumm/speedrun
fi

# Untracked files elsewhere are not part of `git diff`; make that visible.
untracked="$(git -C "$SCUMMVM" ls-files --others --exclude-standard)"
if [[ -n "$untracked" ]]; then
    echo "warning: untracked files outside engines/scumm/speedrun/ are NOT exported:" >&2
    sed 's/^/  /' <<<"$untracked" >&2
fi

# Fixed prefixes/no colour/no external diff so user git config can't produce
# a patch that `git apply` rejects.
git -C "$SCUMMVM" diff --binary --no-color --no-ext-diff --src-prefix=a/ --dst-prefix=b/ \
    "$SCUMMVM_TAG" -- . > "$PATCH"

if [[ ! -s "$PATCH" ]]; then
    rm -f "$PATCH"
    echo "no changes against $SCUMMVM_TAG; no patch written"
else
    echo "wrote patches/$PATCH_NAME ($(wc -l < "$PATCH") lines)"
fi

# The exported patch is the full diff against the tag, so any other patch
# files would be applied on top of it twice.
for p in "$PATCHES"/*.patch; do
    [[ -e "$p" && "$p" != "$PATCH" ]] || continue
    echo "warning: patches/${p##*/} also exists; build-scummvm.sh applies it after $PATCH_NAME" >&2
done

git -C "$SCUMMVM" diff --stat "$SCUMMVM_TAG"
