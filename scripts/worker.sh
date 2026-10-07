#!/usr/bin/env bash
set -euo pipefail
MODEL="${MODEL:?MODEL required}"; AGENT="${AGENT:-build}"; PROMPT_FILE="${PROMPT_FILE:?}"
SELECTION_FILE="${SELECTION_FILE:?}"; PROTECTED="${PROTECTED_PATHS_FILE:?}"; VALIDATE="${VALIDATION_COMMAND:-git diff --check}"
ATTEMPT="${ATTEMPT_ID:?}"; BASE="${BASE_SHA:?}"; PREPARED="${PREPARED_HEAD:?}"; MERGE_CONFLICT="${MERGE_CONFLICT:-false}"
WORKER_SECONDS="${WORKER_SECONDS:-540}"; OUT="${EVIDENCE_DIR:-.opencode-evidence}"; ROOT="${OCA_ACTION_ROOT:?}"
[[ -f "$PROMPT_FILE" && -f "$SELECTION_FILE" && -f "$PROTECTED" ]] || { echo "worker inputs missing" >&2; exit 64; }
[[ "$(/usr/bin/git rev-parse HEAD)" == "$PREPARED" ]] || { echo "prepared HEAD moved before model" >&2; exit 67; }
mkdir -p "$OUT"; prompt="$OUT/prompt.txt"; events="$OUT/opencode.ndjson"; stderr="$OUT/opencode.stderr"; vlog="$OUT/prepublish-validation.log"
start="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
{
  cat "$PROMPT_FILE"
  printf '\n\n<deterministic_frontier_context>\n'; cat "$SELECTION_FILE"; printf '\n</deterministic_frontier_context>\n'
  printf '\nMerge conflicts present at start: %s\n' "$MERGE_CONFLICT"
  cat <<'POLICY'
Execution boundary:
- GitHub state above is context only. Do not call gh or mutate GitHub.
- Do not commit, push, rebase, reset, switch branches, change Git remotes/config, or alter GitHub Actions command files.
- Do not weaken or modify protected control-plane paths.
- Resolve any existing merge conflicts before other work.
- Leave one coherent implementation candidate in the worktree.
POLICY
} > "$prompt"

baseline="$OUT/processes.before"; after="$OUT/processes.after"
/usr/bin/ps -u "$(/usr/bin/id -u)" -o pid= | /usr/bin/awk '{$1=$1;print}' | sort -n > "$baseline"
set +e
env -u GH_TOKEN -u GITHUB_TOKEN -u GITHUB_ACTION_PATH -u OCA_ACTION_ROOT   /usr/bin/timeout --signal=TERM --kill-after=15s "$WORKER_SECONDS"   opencode run --format json --model "$MODEL" --agent "$AGENT" "$(cat "$prompt")" >"$events" 2>"$stderr"
oc_status=$?
set -e
/usr/bin/ps -u "$(/usr/bin/id -u)" -o pid= | /usr/bin/awk '{$1=$1;print}' | sort -n > "$after"
/usr/bin/comm -13 "$baseline" "$after" | while read -r pid; do
  [[ -z "$pid" || "$pid" == "$$" || "$pid" == "$PPID" ]] && continue
  /bin/kill -TERM "$pid" 2>/dev/null || true
done
/bin/sleep 1
/usr/bin/comm -13 "$baseline" "$after" | while read -r pid; do
  [[ -z "$pid" || "$pid" == "$$" || "$pid" == "$PPID" ]] && continue
  /bin/kill -KILL "$pid" 2>/dev/null || true
done

if [[ $oc_status -ne 0 ]]; then
  /usr/bin/jq -n --arg attempt "$ATTEMPT" --arg base "$BASE" --arg model "$MODEL" --arg agent "$AGENT"     --arg started "$start" --arg ended "$(date -u +%Y-%m-%dT%H:%M:%SZ)" --argjson exit "$oc_status"     '{schema:2,kind:"agent-attempt",attempt_id:$attempt,base_sha:$base,model:$model,agent:$agent,status:"opencode_failed",opencode_exit:$exit,started_at:$started,ended_at:$ended}' > "$OUT/evidence.json"
  exit "$oc_status"
fi

[[ "$(/usr/bin/git rev-parse HEAD)" == "$PREPARED" ]] || { echo "::error::model changed Git HEAD" >&2; exit 68; }
if /usr/bin/git diff --name-only --diff-filter=U | /usr/bin/grep -q .; then
  echo "::error::unresolved merge conflicts" >&2; exit 69
fi
/usr/bin/python3 "$ROOT/scripts/check-protected.py" --rules "$PROTECTED" --base "$BASE" --head WORKTREE

set +e
/usr/bin/bash -euo pipefail -c "$VALIDATE" >"$vlog" 2>&1
validation_status=$?
set -e
/usr/bin/git diff --binary "$BASE" > "$OUT/worktree.diff"; /usr/bin/git status --porcelain=v1 > "$OUT/status.txt"
issue="$(/usr/bin/python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["issue"]["number"])' "$SELECTION_FILE")"
sessions="$(/usr/bin/jq -r 'select(.sessionID != null) | .sessionID' "$events" 2>/dev/null | sort -u | /usr/bin/jq -R -s 'split("\n") | map(select(length>0))')"
events_sha="$(/usr/bin/sha256sum "$events" | /usr/bin/awk '{print $1}')"; diff_sha="$(/usr/bin/sha256sum "$OUT/worktree.diff" | /usr/bin/awk '{print $1}')"
validation_sha="$(/usr/bin/sha256sum "$vlog" | /usr/bin/awk '{print $1}')"
/usr/bin/jq -n --arg attempt "$ATTEMPT" --arg base "$BASE" --arg model "$MODEL" --arg agent "$AGENT"   --arg started "$start" --arg ended "$(date -u +%Y-%m-%dT%H:%M:%SZ)" --arg events_sha "$events_sha" --arg diff_sha "$diff_sha"   --arg validation_sha "$validation_sha" --argjson issue "$issue" --argjson sessions "$sessions" --argjson opencode_exit "$oc_status"   --argjson validation_exit "$validation_status"   '{schema:2,kind:"agent-attempt",attempt_id:$attempt,issue_number:$issue,base_sha:$base,model:$model,agent:$agent,status:(if $validation_exit==0 then "prevalidated" else "validation_failed" end),opencode_exit:$opencode_exit,validation_exit:$validation_exit,session_ids:$sessions,opencode_ndjson_sha256:$events_sha,worktree_diff_sha256:$diff_sha,validation_log_sha256:$validation_sha,started_at:$started,ended_at:$ended}' > "$OUT/evidence.json"
[[ $validation_status -eq 0 ]]
