#!/usr/bin/env bash
set -euo pipefail
REMOTE="${TRAJECTORY_REMOTE:-origin}"
BRANCH="${TRAJECTORY_BRANCH:-opencode/trajectory}"
LEASE_SECONDS="${LEASE_SECONDS:-900}"
STATE_FILE="trajectory.json"
WORKTREE="${RUNNER_TEMP:-/tmp}/opencode-trajectory-${GITHUB_RUN_ID:-$$}-${GITHUB_RUN_ATTEMPT:-1}"
remote_sha() { git ls-remote --heads "$REMOTE" "refs/heads/$BRANCH" | awk '{print $1}'; }
init_branch() {
  local current json blob tree commit
  current="$(remote_sha)"
  [[ -n "$current" ]] && { printf '%s\n' "$current"; return 0; }
  json='{"schema":1,"version":0,"status":"idle","lease":null,"last_attempt":null,"last_candidate":null,"last_evidence":null}'
  blob="$(printf '%s\n' "$json" | git hash-object -w --stdin)"
  tree="$(printf '100644 blob %s\t%s\n' "$blob" "$STATE_FILE" | git mktree)"
  commit="$(printf '%s\n' 'chore(trajectory): initialize' | git -c user.name='opencode-actions[bot]' -c user.email='opencode-actions[bot]@users.noreply.github.com' commit-tree "$tree")"
  git push -q "$REMOTE" "$commit:refs/heads/$BRANCH" 2>/dev/null || true
  current="$(remote_sha)"
  [[ -n "$current" ]] || { echo "failed to initialize trajectory branch" >&2; exit 3; }
  printf '%s\n' "$current"
}
checkout_state() {
  local sha="$1"
  rm -rf "$WORKTREE"
  git worktree add --detach -q "$WORKTREE" "$sha"
  trap 'git worktree remove --force "$WORKTREE" >/dev/null 2>&1 || true' EXIT
}
commit_and_cas() {
  local expected="$1" message="$2" next
  git -C "$WORKTREE" config user.name "opencode-actions[bot]"
  git -C "$WORKTREE" config user.email "opencode-actions[bot]@users.noreply.github.com"
  git -C "$WORKTREE" add "$STATE_FILE"
  git -C "$WORKTREE" commit -qm "$message"
  next="$(git -C "$WORKTREE" rev-parse HEAD)"
  git push -q "$REMOTE" "$next:refs/heads/$BRANCH" --force-with-lease="refs/heads/$BRANCH:$expected"
  printf '%s\n' "$next"
}
case "${1:-}" in
  acquire)
    base_sha="${2:?base sha required}"; attempt_id="${3:?attempt id required}"
    expected="$(init_branch)"
    git fetch -q "$REMOTE" "refs/heads/$BRANCH:refs/remotes/$REMOTE/$BRANCH"
    checkout_state "$expected"
    now="$(date +%s)"
    active="$(jq -r '.status == "leased" and (.lease.expires_epoch // 0) > '"$now" "$WORKTREE/$STATE_FILE")"
    if [[ "$active" == "true" ]]; then
      jq -n --arg attempt "$(jq -r '.lease.attempt' "$WORKTREE/$STATE_FILE")" --argjson expires "$(jq -r '.lease.expires_epoch' "$WORKTREE/$STATE_FILE")" '{acquired:false,active_attempt:$attempt,expires_epoch:$expires}'
      exit 0
    fi
    lease="$(printf '%s:%s:%s' "$attempt_id" "$base_sha" "$expected" | sha256sum | cut -d' ' -f1)"
    version="$(jq -r '.version // 0' "$WORKTREE/$STATE_FILE")"
    expires="$((now + LEASE_SECONDS))"
    jq --arg lease "$lease" --arg attempt "$attempt_id" --arg base "$base_sha" --arg run "${GITHUB_RUN_ID:-local}" --argjson version "$((version+1))"       '.version=$version | .status="leased" | .lease={token:$lease,attempt:$attempt,base_sha:$base,run_id:$run,expires_epoch:$expires} | .last_attempt=$attempt'       "$WORKTREE/$STATE_FILE" > "$WORKTREE/$STATE_FILE.tmp"
    mv "$WORKTREE/$STATE_FILE.tmp" "$WORKTREE/$STATE_FILE"
    next="$(commit_and_cas "$expected" "chore(trajectory): acquire $attempt_id")"
    jq -n --arg token "$lease" --arg trajectory "$next" --arg branch "$BRANCH" '{acquired:true,lease_token:$token,trajectory_sha:$trajectory,branch:$branch}'
    ;;
  finalize)
    expected="${2:?trajectory sha required}"; lease="${3:?lease token required}"; status="${4:?status required}"
    candidate="${5:-}"; evidence="${6:-}"
    git fetch -q "$REMOTE" "refs/heads/$BRANCH:refs/remotes/$REMOTE/$BRANCH"
    current="$(remote_sha)"
    [[ "$current" == "$expected" ]] || { echo "stale trajectory: expected $expected current $current" >&2; exit 42; }
    checkout_state "$current"
    actual="$(jq -r '.lease.token // empty' "$WORKTREE/$STATE_FILE")"
    [[ "$actual" == "$lease" ]] || { echo "lease mismatch" >&2; exit 43; }
    jq --arg status "$status" --arg candidate "$candidate" --arg evidence "$evidence"       '.status=$status | .last_candidate=(if $candidate=="" then .last_candidate else $candidate end) | .last_evidence=(if $evidence=="" then .last_evidence else $evidence end) | .lease=null'       "$WORKTREE/$STATE_FILE" > "$WORKTREE/$STATE_FILE.tmp"
    mv "$WORKTREE/$STATE_FILE.tmp" "$WORKTREE/$STATE_FILE"
    commit_and_cas "$current" "chore(trajectory): finalize $status" >/dev/null
    ;;
  read)
    sha="$(init_branch)"; git show "$sha:$STATE_FILE"
    ;;
  *) echo "usage: $0 acquire BASE_SHA ATTEMPT_ID | finalize TRAJECTORY_SHA LEASE STATUS [CANDIDATE] [EVIDENCE] | read" >&2; exit 2 ;;
esac
