#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
T="$(mktemp -d)"
trap 'rm -rf "$T"' EXIT

/usr/bin/git init -q --bare "$T/remote.git"
/usr/bin/git init -q "$T/work"
cd "$T/work"
/usr/bin/git config user.name test
/usr/bin/git config user.email test@example.com
echo seed > README.md
/usr/bin/git add README.md
/usr/bin/git commit -qm init
/usr/bin/git branch -M main
/usr/bin/git remote add origin "$T/remote.git"
/usr/bin/git push -q -u origin main
base="$(/usr/bin/git rev-parse HEAD)"

lease1="$(TRAJECTORY_BRANCH=opencode/trajectory LEASE_SECONDS=900 RUNNER_TEMP="$T/t1" GITHUB_RUN_ID=1 GITHUB_RUN_ATTEMPT=1   /usr/bin/bash "$ROOT/scripts/trajectory.sh" acquire "$base" attempt-1)"
test "$(/usr/bin/jq -r .acquired <<<"$lease1")" = true

lease2="$(TRAJECTORY_BRANCH=opencode/trajectory LEASE_SECONDS=900 RUNNER_TEMP="$T/t2" GITHUB_RUN_ID=2 GITHUB_RUN_ATTEMPT=1   /usr/bin/bash "$ROOT/scripts/trajectory.sh" acquire "$base" attempt-2)"
test "$(/usr/bin/jq -r .acquired <<<"$lease2")" = false
test "$(/usr/bin/jq -r .reason <<<"$lease2")" = lease_active

tsha="$(/usr/bin/jq -r .trajectory_sha <<<"$lease1")"
token="$(/usr/bin/jq -r .lease_token <<<"$lease1")"
TRAJECTORY_BRANCH=opencode/trajectory RUNNER_TEMP="$T/t3"   /usr/bin/bash "$ROOT/scripts/trajectory.sh" finalize "$tsha" "$token" validated "$base" evidence:test 7 11

state="$(TRAJECTORY_BRANCH=opencode/trajectory RUNNER_TEMP="$T/t4" /usr/bin/bash "$ROOT/scripts/trajectory.sh" read)"
test "$(/usr/bin/jq -r .schema <<<"$state")" = 2
test "$(/usr/bin/jq -r .status <<<"$state")" = validated
test "$(/usr/bin/jq -r .last_base <<<"$state")" = "$base"
test "$(/usr/bin/jq -r .last_candidate <<<"$state")" = "$base"
test "$(/usr/bin/jq -r .last_issue <<<"$state")" = 7
test "$(/usr/bin/jq -r .last_pr <<<"$state")" = 11

# Candidate == canonical base means previous state has already landed; next work may proceed.
lease3="$(TRAJECTORY_BRANCH=opencode/trajectory LEASE_SECONDS=900 RUNNER_TEMP="$T/t5" GITHUB_RUN_ID=3 GITHUB_RUN_ATTEMPT=1   /usr/bin/bash "$ROOT/scripts/trajectory.sh" acquire "$base" attempt-3)"
test "$(/usr/bin/jq -r .acquired <<<"$lease3")" = true

# The old lease cannot finalize after the trajectory ref moved.
if TRAJECTORY_BRANCH=opencode/trajectory RUNNER_TEMP="$T/t6"   /usr/bin/bash "$ROOT/scripts/trajectory.sh" finalize "$tsha" "$token" validated "$base" stale; then
  echo "stale finalize unexpectedly succeeded" >&2
  exit 1
fi

echo "trajectory tests passed"
