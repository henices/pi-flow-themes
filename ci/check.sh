#!/usr/bin/env bash
# ci/check.sh — the entire verification pipeline as one self-contained script.
# No CI service required: a local git hook, cron, or any forge's CI only needs to run this.
#
# Steps:
#   1. determinism        two consecutive builds must be byte-identical
#   2. themes/ in sync    committed JSON == fresh build (git worktrees only, skipped otherwise)
#   3. --check            contrast floors + KNOWN allowlist + canvas ceilings + near-duplicates
#                         + sources/theme-sources.json completeness
#   4. pi loader          every theme loaded through pi's real validator + loader
#
# Requirements: python3 (stdlib only); node >= 22.19 + npm for step 4 (network on first run,
# node_modules/ is cached and gitignored). PI_VERSION pins the loader (default 0.85.1).
set -euo pipefail
cd "$(dirname "$0")/.."
PY=${PYTHON:-python3}
NODE=${NODE:-node}
NPM=${NPM:-npm}
PI_VERSION=${PI_VERSION:-0.85.1}

echo "== 1/4 determinism: two consecutive builds must be byte-identical"
sig() { find themes -name 'flow-*.json' -print0 | sort -z | xargs -0 sha1sum | sha1sum; }
"$PY" build_themes.py >/dev/null
a=$(sig)
"$PY" build_themes.py >/dev/null
b=$(sig)
if [ "$a" != "$b" ]; then
  echo "FAIL: two consecutive builds differ"; exit 1
fi
echo "ok  ${a%% *}"

echo "== 2/4 themes/ in sync with THEMES"
if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  if [ -n "$(git status --porcelain -- themes/)" ]; then
    git status --short -- themes/
    echo "FAIL: themes/ differs from a fresh build (run build_themes.py and commit, or fix THEMES)"
    exit 1
  fi
  echo "ok"
else
  echo "skip (not a git worktree)"
fi

echo "== 3/4 build_themes.py --check (floors / allowlist / sources / duplicates)"
"$PY" build_themes.py --check

echo "== 4/4 load all themes through pi ${PI_VERSION}'s own validator + loader"
if [ ! -d node_modules/@earendil-works/pi-coding-agent ]; then
  "$NPM" install --omit=dev --ignore-scripts --no-fund --no-audit \
    "@earendil-works/pi-coding-agent@$PI_VERSION" >/dev/null
fi
"$NODE" ci/pi-validate.mjs

echo "ALL CHECKS PASSED"
