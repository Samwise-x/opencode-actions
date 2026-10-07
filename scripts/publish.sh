#!/usr/bin/env bash
set -euo pipefail

: "${GH_TOKEN:?GH_TOKEN required}"
: "${GITHUB_REPOSITORY:?GITHUB_REPOSITORY required}"
ATTEMPT="${ATTEMPT_ID:?}"; BASE="${BASE_SHA:?}"; ISSUE="${ISSUE_NUMBER:?}"; BRANCH="${CANDIDATE_BRANCH:?}"
EXPECTED="${EXPECTED_REMOTE_HEAD:-}"; OUT="${EVIDENCE_DIR:-.opencode-evidence}"; ROOT="${OCA_ACTION_ROOT:?}"
SOURCE="$GITHUB_WORKSPACE"
TARGET="$(mktemp -d "${RUNNER_TEMP:-/tmp}/opencode-publish.XXXXXX")"
trap 'rm -rf "$TARGET"' EXIT

auth="$(printf 'x-access-token:%s' "$GH_TOKEN" | /usr/bin/base64 -w0)"
remote="${GITHUB_SERVER_URL:-https://github.com}/${GITHUB_REPOSITORY}.git"
GIT_AUTH=(-c "http.https://github.com/.extraheader=AUTHORIZATION: basic $auth" -c core.hooksPath=/dev/null)

/usr/bin/git init -q "$TARGET"
/usr/bin/git -C "$TARGET" config core.hooksPath /dev/null
/usr/bin/git -C "$TARGET" config user.name "opencode-actions[bot]"
/usr/bin/git -C "$TARGET" config user.email "opencode-actions[bot]@users.noreply.github.com"
/usr/bin/git -C "$TARGET" remote add origin "$remote"
/usr/bin/git -C "$TARGET" "${GIT_AUTH[@]}" fetch -q --no-tags origin "$BASE"
if [[ -n "$EXPECTED" ]]; then
  /usr/bin/git -C "$TARGET" "${GIT_AUTH[@]}" fetch -q --no-tags origin "$EXPECTED"
  /usr/bin/git -C "$TARGET" checkout -q --detach "$EXPECTED"
  set +e
  /usr/bin/git -C "$TARGET" merge --no-commit --no-ff "$BASE" >/dev/null 2>&1
  merge_rc=$?
  set -e
  [[ $merge_rc -eq 0 || -f "$TARGET/.git/MERGE_HEAD" ]] || { echo "failed to reconstruct candidate merge" >&2; exit 73; }
else
  /usr/bin/git -C "$TARGET" checkout -q --detach "$BASE"
fi

/usr/bin/rsync -a --delete   --exclude='.git'   --exclude='.opencode-evidence'   "$SOURCE/" "$TARGET/"

cd "$TARGET"
if /usr/bin/git diff --name-only --diff-filter=U | /usr/bin/grep -q .; then
  echo "reconstructed candidate still contains unresolved conflicts" >&2
  exit 74
fi

/usr/bin/python3 "$ROOT/scripts/check-protected.py"   --rules "$SOURCE/$PROTECTED_PATHS_FILE"   --base "$BASE"   --head WORKTREE

/usr/bin/git add -A
if ! /usr/bin/git diff --cached --quiet || /usr/bin/git rev-parse -q --verify MERGE_HEAD >/dev/null 2>&1; then
  /usr/bin/git commit --no-verify     -m "agent: advance issue #$ISSUE"     -m "OpenCode-Attempt: $ATTEMPT"     -m "OpenCode-Issue: #$ISSUE"
fi
candidate="$(/usr/bin/git rev-parse HEAD)"
/usr/bin/git merge-base --is-ancestor "$BASE" "$candidate" || { echo "candidate is not descended from canonical base" >&2; exit 75; }

if [[ "$candidate" != "$BASE" ]]; then
  if [[ -n "$EXPECTED" ]]; then
    /usr/bin/git "${GIT_AUTH[@]}" push origin       --force-with-lease="refs/heads/$BRANCH:$EXPECTED"       "$candidate:refs/heads/$BRANCH"
  else
    /usr/bin/git "${GIT_AUTH[@]}" push origin "$candidate:refs/heads/$BRANCH"
  fi
fi

cd "$SOURCE"
/usr/bin/jq --arg candidate "$candidate" --arg branch "$BRANCH" --argjson issue "$ISSUE"   '.candidate_sha=$candidate | .candidate_branch=$branch | .issue_number=$issue'   "$OUT/evidence.json" > "$OUT/evidence.tmp"
mv "$OUT/evidence.tmp" "$OUT/evidence.json"
/usr/bin/sha256sum "$OUT/evidence.json" | /usr/bin/awk '{print $1}' > "$OUT/evidence.sha256"
printf '%s\n' "$candidate"
