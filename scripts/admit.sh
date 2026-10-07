#!/usr/bin/env bash
set -euo pipefail
TARGET="${TARGET_BRANCH:-main}"
EXPECTED="${EXPECTED_BASE_SHA:?EXPECTED_BASE_SHA required}"
CANDIDATE="${CANDIDATE_SHA:?CANDIDATE_SHA required}"
EVIDENCE="${EVIDENCE_FILE:?EVIDENCE_FILE required}"
jq -e --arg base "$EXPECTED" --arg candidate "$CANDIDATE" '
  .schema == 1 and
  .base_sha == $base and
  .candidate_sha == $candidate and
  .status == "validated" and
  .opencode_exit == 0 and
  .validation_exit == 0
' "$EVIDENCE" >/dev/null
git fetch -q origin "$TARGET"
current="$(git rev-parse "origin/$TARGET")"
[[ "$current" == "$EXPECTED" ]] || { echo "stale base: expected $EXPECTED current $current" >&2; exit 42; }
git fetch -q origin "$CANDIDATE" || true
git cat-file -e "$CANDIDATE^{commit}"
git merge-base --is-ancestor "$EXPECTED" "$CANDIDATE"
git push origin "$CANDIDATE:refs/heads/$TARGET" --force-with-lease="refs/heads/$TARGET:$EXPECTED"
