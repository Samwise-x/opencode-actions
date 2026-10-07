#!/usr/bin/env bash
set -euo pipefail
ATTEMPT="${ATTEMPT_ID:?ATTEMPT_ID required}"
BASE="${BASE_SHA:?BASE_SHA required}"
OUT="${EVIDENCE_DIR:-.opencode-evidence}"
BRANCH="opencode/attempt/${ATTEMPT}"
git config user.name "opencode-actions[bot]"
git config user.email "opencode-actions[bot]@users.noreply.github.com"
git add -A -- ':!.opencode-evidence'
if git diff --cached --quiet; then
  candidate="$BASE"
else
  git commit -m "opencode: attempt ${ATTEMPT}"
  candidate="$(git rev-parse HEAD)"
  git push origin "HEAD:refs/heads/$BRANCH"
fi
jq --arg candidate "$candidate" --arg branch "$BRANCH" '.candidate_sha=$candidate | .candidate_branch=$branch' "$OUT/evidence.json" > "$OUT/evidence.tmp"
mv "$OUT/evidence.tmp" "$OUT/evidence.json"
sha256sum "$OUT/evidence.json" | awk '{print $1}' > "$OUT/evidence.sha256"
printf '%s\n' "$candidate"
