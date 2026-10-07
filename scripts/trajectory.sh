#!/usr/bin/env bash
set -euo pipefail

: "${GH_TOKEN:?GH_TOKEN required}"
: "${GITHUB_REPOSITORY:?GITHUB_REPOSITORY required}"

BRANCH="${TRAJECTORY_BRANCH:-opencode/trajectory}"
LEASE_SECONDS="${LEASE_SECONDS:-900}"
REQUIRED_CHECKS="${TRAJECTORY_REQUIRED_CHECKS:-deterministic,security}"
STATE_FILE="trajectory.json"
TMP_PARENT="${RUNNER_TEMP:-/tmp}"
mkdir -p "$TMP_PARENT"
ROOT="$(mktemp -d "$TMP_PARENT/opencode-trajectory.XXXXXX")"
trap 'rm -rf "$ROOT"' EXIT
REPO="$ROOT/repo"

gitx() { /usr/bin/git -C "$REPO" "$@"; }

auth="$(printf 'x-access-token:%s' "$GH_TOKEN" | /usr/bin/base64 -w0)"
remote="${TRAJECTORY_REMOTE_URL:-${GITHUB_SERVER_URL:-https://github.com}/${GITHUB_REPOSITORY}.git}"
mkdir -p "$REPO"
/usr/bin/git init -q "$REPO"
gitx config core.hooksPath /dev/null
gitx config user.name "opencode-actions[bot]"
gitx config user.email "opencode-actions[bot]@users.noreply.github.com"
gitx remote add origin "$remote"
GIT_AUTH=(-c "http.https://github.com/.extraheader=AUTHORIZATION: basic $auth" -c core.hooksPath=/dev/null)

remote_sha() {
  gitx "${GIT_AUTH[@]}" ls-remote --heads origin "refs/heads/$BRANCH" | /usr/bin/awk '{print $1}'
}

fetch_branch() {
  gitx "${GIT_AUTH[@]}" fetch -q --no-tags origin "refs/heads/$BRANCH:refs/remotes/origin/$BRANCH"
}

init_branch() {
  local current json blob tree commit
  current="$(remote_sha)"
  [[ -n "$current" ]] && { printf '%s\n' "$current"; return 0; }
  json='{"schema":2,"version":0,"status":"idle","lease":null,"last_attempt":null,"last_base":null,"last_candidate":null,"last_evidence":null,"last_issue":null,"last_pr":null}'
  blob="$(printf '%s\n' "$json" | gitx hash-object -w --stdin)"
  tree="$(printf '100644 blob %s\t%s\n' "$blob" "$STATE_FILE" | gitx mktree)"
  commit="$(printf '%s\n' 'chore(trajectory): initialize' | gitx commit-tree "$tree")"
  gitx "${GIT_AUTH[@]}" push -q origin "$commit:refs/heads/$BRANCH" 2>/dev/null || true
  current="$(remote_sha)"
  [[ -n "$current" ]] || { echo "failed to initialize trajectory branch" >&2; exit 3; }
  printf '%s\n' "$current"
}

checkout_state() {
  local sha="$1"
  fetch_branch
  gitx checkout -q --detach "$sha"
}

commit_and_cas() {
  local expected="$1" message="$2" next
  gitx add "$STATE_FILE"
  gitx commit -qm "$message" --no-verify
  next="$(gitx rev-parse HEAD)"
  gitx "${GIT_AUTH[@]}" push -q origin "$next:refs/heads/$BRANCH"     --force-with-lease="refs/heads/$BRANCH:$expected"
  printf '%s\n' "$next"
}

candidate_reachable_from_base() {
  local candidate="$1" base="$2" status rc
  [[ "$candidate" == "$base" ]] && return 0
  set +e
  status="$(/usr/bin/gh api "repos/$GITHUB_REPOSITORY/compare/$candidate...$base" --jq .status 2>/dev/null)"
  rc=$?
  set -e
  [[ $rc -eq 0 && ( "$status" == "ahead" || "$status" == "identical" ) ]]
}

check_state() {
  local candidate="$1" json pending=0 failed=0 name row status conclusion
  json="$(/usr/bin/gh api -H 'Accept: application/vnd.github+json' "repos/$GITHUB_REPOSITORY/commits/$candidate/check-runs?per_page=100")"
  IFS=',' read -r -a required <<< "$REQUIRED_CHECKS"
  for name in "${required[@]}"; do
    name="$(echo "$name" | xargs)"
    [[ -z "$name" ]] && continue
    row="$(/usr/bin/jq -c --arg n "$name" '[.check_runs[] | select(.name==$n)] | sort_by(.id) | last // empty' <<<"$json")"
    if [[ -z "$row" ]]; then pending=1; continue; fi
    status="$(/usr/bin/jq -r .status <<<"$row")"
    conclusion="$(/usr/bin/jq -r '.conclusion // ""' <<<"$row")"
    if [[ "$status" != "completed" ]]; then pending=1
    elif [[ "$conclusion" != "success" ]]; then failed=1
    fi
  done
  if [[ $failed -eq 1 ]]; then echo failed
  elif [[ $pending -eq 1 ]]; then echo pending
  else echo success
  fi
}

case "${1:-}" in
  acquire)
    base_sha="${2:?base sha required}"; attempt_id="${3:?attempt id required}"
    expected="$(init_branch)"
    checkout_state "$expected"
    now="$(date +%s)"
    active="$(/usr/bin/jq -r --argjson now "$now" '.status=="leased" and (.lease.expires_epoch // 0)>$now' "$REPO/$STATE_FILE")"
    if [[ "$active" == "true" ]]; then
      /usr/bin/jq -n --arg attempt "$(/usr/bin/jq -r '.lease.attempt' "$REPO/$STATE_FILE")"         --argjson expires "$(/usr/bin/jq -r '.lease.expires_epoch' "$REPO/$STATE_FILE")"         '{acquired:false,reason:"lease_active",active_attempt:$attempt,expires_epoch:$expires}'
      exit 0
    fi

    prior_status="$(/usr/bin/jq -r '.status' "$REPO/$STATE_FILE")"
    last_candidate="$(/usr/bin/jq -r '.last_candidate // empty' "$REPO/$STATE_FILE")"
    last_base="$(/usr/bin/jq -r '.last_base // empty' "$REPO/$STATE_FILE")"
    if [[ "$prior_status" == "validated" && -n "$last_candidate" ]]; then
      if candidate_reachable_from_base "$last_candidate" "$base_sha"; then
        :
      elif [[ -n "$last_base" && "$last_base" != "$base_sha" ]]; then
        :
      else
        gate_state="$(check_state "$last_candidate")"
        if [[ "$gate_state" == "pending" ]]; then
          /usr/bin/jq -n --arg candidate "$last_candidate" '{acquired:false,reason:"validation_pending",candidate_sha:$candidate}'
          exit 0
        fi
        if [[ "$gate_state" == "success" ]]; then
          /usr/bin/jq -n --arg candidate "$last_candidate" '{acquired:false,reason:"admission_pending",candidate_sha:$candidate}'
          exit 0
        fi
      fi
    fi

    lease="$(printf '%s:%s:%s' "$attempt_id" "$base_sha" "$expected" | /usr/bin/sha256sum | cut -d' ' -f1)"
    version="$(/usr/bin/jq -r '.version // 0' "$REPO/$STATE_FILE")"
    expires="$((now + LEASE_SECONDS))"
    /usr/bin/jq --arg lease "$lease" --arg attempt "$attempt_id" --arg base "$base_sha"       --arg run "${GITHUB_RUN_ID:-local}" --argjson version "$((version+1))" --argjson expires "$expires"       '.version=$version | .status="leased" | .lease={token:$lease,attempt:$attempt,base_sha:$base,run_id:$run,expires_epoch:$expires} | .last_attempt=$attempt'       "$REPO/$STATE_FILE" > "$REPO/$STATE_FILE.tmp"
    mv "$REPO/$STATE_FILE.tmp" "$REPO/$STATE_FILE"
    next="$(commit_and_cas "$expected" "chore(trajectory): acquire $attempt_id")"
    /usr/bin/jq -n --arg token "$lease" --arg trajectory "$next" --arg branch "$BRANCH"       '{acquired:true,reason:"acquired",lease_token:$token,trajectory_sha:$trajectory,branch:$branch}'
    ;;

  finalize)
    expected="${2:?trajectory sha required}"; lease="${3:?lease token required}"; status="${4:?status required}"
    candidate="${5:-}"; evidence="${6:-}"; issue="${7:-}"; pr="${8:-}"
    current="$(remote_sha)"
    [[ "$current" == "$expected" ]] || { echo "stale trajectory: expected $expected current $current" >&2; exit 42; }
    checkout_state "$current"
    actual="$(/usr/bin/jq -r '.lease.token // empty' "$REPO/$STATE_FILE")"
    [[ "$actual" == "$lease" ]] || { echo "lease mismatch" >&2; exit 43; }
    lease_base="$(/usr/bin/jq -r '.lease.base_sha // empty' "$REPO/$STATE_FILE")"
    /usr/bin/jq --arg status "$status" --arg candidate "$candidate" --arg evidence "$evidence"       --arg base "$lease_base" --arg issue "$issue" --arg pr "$pr"       '.status=$status
       | .last_base=(if $candidate=="" then .last_base else $base end)
       | .last_candidate=(if $candidate=="" then .last_candidate else $candidate end)
       | .last_evidence=(if $evidence=="" then .last_evidence else $evidence end)
       | .last_issue=(if $issue=="" then .last_issue else ($issue|tonumber) end)
       | .last_pr=(if $pr=="" then .last_pr else ($pr|tonumber) end)
       | .lease=null'       "$REPO/$STATE_FILE" > "$REPO/$STATE_FILE.tmp"
    mv "$REPO/$STATE_FILE.tmp" "$REPO/$STATE_FILE"
    commit_and_cas "$current" "chore(trajectory): finalize $status" >/dev/null
    ;;

  read)
    sha="$(init_branch)"; checkout_state "$sha"; cat "$REPO/$STATE_FILE"
    ;;

  *)
    echo "usage: $0 acquire BASE_SHA ATTEMPT_ID | finalize TRAJECTORY_SHA LEASE STATUS [CANDIDATE] [EVIDENCE] [ISSUE] [PR] | read" >&2
    exit 2
    ;;
esac
