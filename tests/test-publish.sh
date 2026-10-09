#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
T="$(mktemp -d)"
trap 'rm -rf "$T"' EXIT
remote="$T/remote.git"
source="$T/source"
mkdir -p "$source" "$T/evidence" "$T/runner"
/usr/bin/git init -q --bare "$remote"
/usr/bin/git init -q -b main "$source"
/usr/bin/git -C "$source" config user.name test
/usr/bin/git -C "$source" config user.email test@example.com
mkdir -p "$source/.opencode-actions"
printf '.github/workflows/**\n' > "$source/.opencode-actions/protected-paths.txt"
printf 'base\n' > "$source/app.txt"
/usr/bin/git -C "$source" add .
/usr/bin/git -C "$source" commit -qm base
/usr/bin/git -C "$source" remote add origin "$remote"
/usr/bin/git -C "$source" push -q -u origin main
base="$(/usr/bin/git -C "$source" rev-parse HEAD)"

attempt="100-1"
cat > "$T/evidence/evidence.json" <<EOF
{"schema":2,"kind":"agent-attempt","attempt_id":"$attempt","issue_number":1,"base_sha":"$base","model":"provider/model","agent":"build","status":"prevalidated","opencode_exit":0,"validation_exit":0,"started_at":"2026-10-09T00:00:00+00:00","ended_at":"2026-10-09T00:01:00+00:00"}
EOF

lease1="$(GH_TOKEN=test GITHUB_REPOSITORY=test/test TRAJECTORY_REMOTE_URL="$remote" RUNNER_TEMP="$T/runner/lease1" GITHUB_RUN_ID=100 bash "$ROOT/scripts/trajectory.sh" acquire "$base" "$attempt")"
test "$(jq -r .acquired <<<"$lease1")" = true
trajectory1="$(jq -r .trajectory_sha <<<"$lease1")"
token1="$(jq -r .lease_token <<<"$lease1")"

printf 'candidate-one\n' >> "$source/app.txt"
candidate1="$(env \
  GH_TOKEN=test \
  GITHUB_REPOSITORY=test/test \
  PUBLISH_REMOTE_URL="$remote" \
  TRAJECTORY_REMOTE_URL="$remote" \
  GITHUB_WORKSPACE="$source" \
  RUNNER_TEMP="$T/runner" \
  ATTEMPT_ID="$attempt" \
  BASE_SHA="$base" \
  ISSUE_NUMBER=1 \
  CANDIDATE_BRANCH=opencode/issue-1 \
  EXPECTED_REMOTE_HEAD= \
  EVIDENCE_DIR="$T/evidence" \
  OCA_ACTION_ROOT="$ROOT" \
  PROTECTED_PATHS_FILE=.opencode-actions/protected-paths.txt \
  TRAJECTORY_SHA="$trajectory1" \
  LEASE_TOKEN="$token1" \
  bash "$ROOT/scripts/publish.sh")"
remote1="$(/usr/bin/git --git-dir="$remote" rev-parse refs/heads/opencode/issue-1)"
test "$remote1" = "$candidate1"

GH_TOKEN=test GITHUB_REPOSITORY=test/test TRAJECTORY_REMOTE_URL="$remote" RUNNER_TEMP="$T/runner/finalize1" \
  bash "$ROOT/scripts/trajectory.sh" finalize "$trajectory1" "$token1" failed

attempt2="101-1"
lease2="$(GH_TOKEN=test GITHUB_REPOSITORY=test/test TRAJECTORY_REMOTE_URL="$remote" RUNNER_TEMP="$T/runner/lease2" GITHUB_RUN_ID=101 bash "$ROOT/scripts/trajectory.sh" acquire "$base" "$attempt2")"
test "$(jq -r .acquired <<<"$lease2")" = true
trajectory2="$(jq -r .trajectory_sha <<<"$lease2")"
token2="$(jq -r .lease_token <<<"$lease2")"

# Simulate ownership disappearing after work started. Publication must not use
# the stale lease even if the candidate branch force-with-lease would succeed.
GH_TOKEN=test GITHUB_REPOSITORY=test/test TRAJECTORY_REMOTE_URL="$remote" RUNNER_TEMP="$T/runner/finalize2" \
  bash "$ROOT/scripts/trajectory.sh" finalize "$trajectory2" "$token2" failed

printf 'candidate-two\n' >> "$source/app.txt"
cat > "$T/evidence/evidence.json" <<EOF
{"schema":2,"kind":"agent-attempt","attempt_id":"$attempt2","issue_number":1,"base_sha":"$base","model":"provider/model","agent":"build","status":"prevalidated","opencode_exit":0,"validation_exit":0,"started_at":"2026-10-09T00:02:00+00:00","ended_at":"2026-10-09T00:03:00+00:00"}
EOF

if env \
  GH_TOKEN=test \
  GITHUB_REPOSITORY=test/test \
  PUBLISH_REMOTE_URL="$remote" \
  TRAJECTORY_REMOTE_URL="$remote" \
  GITHUB_WORKSPACE="$source" \
  RUNNER_TEMP="$T/runner" \
  ATTEMPT_ID="$attempt2" \
  BASE_SHA="$base" \
  ISSUE_NUMBER=1 \
  CANDIDATE_BRANCH=opencode/issue-1 \
  EXPECTED_REMOTE_HEAD="$candidate1" \
  EVIDENCE_DIR="$T/evidence" \
  OCA_ACTION_ROOT="$ROOT" \
  PROTECTED_PATHS_FILE=.opencode-actions/protected-paths.txt \
  TRAJECTORY_SHA="$trajectory2" \
  LEASE_TOKEN="$token2" \
  bash "$ROOT/scripts/publish.sh"; then
  echo "stale lease unexpectedly published" >&2
  exit 1
fi

remote2="$(/usr/bin/git --git-dir="$remote" rev-parse refs/heads/opencode/issue-1)"
test "$remote2" = "$candidate1"

echo "publication lease tests passed"
