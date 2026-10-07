#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
T="$(mktemp -d)"
trap 'rm -rf "$T"' EXIT
git init -q --bare "$T/remote.git"
git init -q "$T/work"
cd "$T/work"
git config user.name test
git config user.email test@example.com
echo seed > README.md
git add README.md
git commit -qm init
git branch -M main
git remote add origin "$T/remote.git"
git push -q -u origin main
base="$(git rev-parse HEAD)"

lease1="$(GH_TOKEN=test GITHUB_REPOSITORY=test/test TRAJECTORY_REMOTE_URL="$T/remote.git" TRAJECTORY_BRANCH=opencode/trajectory LEASE_SECONDS=900 RUNNER_TEMP="$T/t1" GITHUB_RUN_ID=1 GITHUB_RUN_ATTEMPT=1 bash "$ROOT/scripts/trajectory.sh" acquire "$base" attempt-1)"
test "$(jq -r .acquired <<<"$lease1")" = true

lease2="$(GH_TOKEN=test GITHUB_REPOSITORY=test/test TRAJECTORY_REMOTE_URL="$T/remote.git" TRAJECTORY_BRANCH=opencode/trajectory LEASE_SECONDS=900 RUNNER_TEMP="$T/t2" GITHUB_RUN_ID=2 GITHUB_RUN_ATTEMPT=1 bash "$ROOT/scripts/trajectory.sh" acquire "$base" attempt-2)"
test "$(jq -r .acquired <<<"$lease2")" = false

tsha="$(jq -r .trajectory_sha <<<"$lease1")"
token="$(jq -r .lease_token <<<"$lease1")"
GH_TOKEN=test GITHUB_REPOSITORY=test/test TRAJECTORY_REMOTE_URL="$T/remote.git" TRAJECTORY_BRANCH=opencode/trajectory RUNNER_TEMP="$T/t3" bash "$ROOT/scripts/trajectory.sh" finalize "$tsha" "$token" validated "$base" evidence:test

state="$(GH_TOKEN=test GITHUB_REPOSITORY=test/test TRAJECTORY_REMOTE_URL="$T/remote.git" TRAJECTORY_BRANCH=opencode/trajectory RUNNER_TEMP="$T/t4" bash "$ROOT/scripts/trajectory.sh" read)"
test "$(jq -r .status <<<"$state")" = validated
test "$(jq -r .last_candidate <<<"$state")" = "$base"

lease3="$(GH_TOKEN=test GITHUB_REPOSITORY=test/test TRAJECTORY_REMOTE_URL="$T/remote.git" TRAJECTORY_BRANCH=opencode/trajectory LEASE_SECONDS=900 RUNNER_TEMP="$T/t5" GITHUB_RUN_ID=3 GITHUB_RUN_ATTEMPT=1 bash "$ROOT/scripts/trajectory.sh" acquire "$base" attempt-3)"
test "$(jq -r .acquired <<<"$lease3")" = true

if GH_TOKEN=test GITHUB_REPOSITORY=test/test TRAJECTORY_REMOTE_URL="$T/remote.git" TRAJECTORY_BRANCH=opencode/trajectory RUNNER_TEMP="$T/t6" bash "$ROOT/scripts/trajectory.sh" finalize "$tsha" "$token" validated "$base" stale; then
  echo "stale finalize unexpectedly succeeded" >&2
  exit 1
fi

echo "trajectory tests passed"
