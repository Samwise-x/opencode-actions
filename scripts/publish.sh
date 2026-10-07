#!/usr/bin/env bash
set -euo pipefail
ATTEMPT="${ATTEMPT_ID:?}"; BASE="${BASE_SHA:?}"; ISSUE="${ISSUE_NUMBER:?}"; BRANCH="${CANDIDATE_BRANCH:?}"
EXPECTED="${EXPECTED_REMOTE_HEAD:-}"; OUT="${EVIDENCE_DIR:-.opencode-evidence}"
safe_hooks="${RUNNER_TEMP:-/tmp}/opencode-empty-hooks"
mkdir -p "$safe_hooks"
/usr/bin/git config user.name "opencode-actions[bot]"
/usr/bin/git config user.email "opencode-actions[bot]@users.noreply.github.com"
/usr/bin/git add -A -- ':!.opencode-evidence'
if ! /usr/bin/git diff --cached --quiet || /usr/bin/git rev-parse -q --verify MERGE_HEAD >/dev/null 2>&1; then
  /usr/bin/git -c core.hooksPath="$safe_hooks" commit --no-verify     -m "agent: advance issue #$ISSUE"     -m "OpenCode-Attempt: $ATTEMPT"     -m "OpenCode-Issue: #$ISSUE"
fi
candidate="$(/usr/bin/git rev-parse HEAD)"
/usr/bin/git merge-base --is-ancestor "$BASE" "$candidate" || { echo "candidate is not descended from canonical base" >&2; exit 72; }
if [[ "$candidate" != "$BASE" ]]; then
  if [[ -n "$EXPECTED" ]]; then
    /usr/bin/git -c core.hooksPath="$safe_hooks" push origin       --force-with-lease="refs/heads/$BRANCH:$EXPECTED"       "$candidate:refs/heads/$BRANCH"
  else
    /usr/bin/git -c core.hooksPath="$safe_hooks" push origin "$candidate:refs/heads/$BRANCH"
  fi
fi
/usr/bin/jq --arg candidate "$candidate" --arg branch "$BRANCH" --argjson issue "$ISSUE"   '.candidate_sha=$candidate | .candidate_branch=$branch | .issue_number=$issue'   "$OUT/evidence.json" > "$OUT/evidence.tmp"
mv "$OUT/evidence.tmp" "$OUT/evidence.json"
/usr/bin/sha256sum "$OUT/evidence.json" | /usr/bin/awk '{print $1}' > "$OUT/evidence.sha256"
printf '%s\n' "$candidate"
