#!/usr/bin/env bash
set -euo pipefail
MODEL="${MODEL:?MODEL required}"
AGENT="${AGENT:-build}"
PROMPT_FILE="${PROMPT_FILE:?PROMPT_FILE required}"
VALIDATE="${VALIDATION_COMMAND:?VALIDATION_COMMAND required}"
OUT="${EVIDENCE_DIR:-.opencode-evidence}"
ATTEMPT="${ATTEMPT_ID:?ATTEMPT_ID required}"
BASE="$(git rev-parse HEAD)"
[[ -f "$PROMPT_FILE" ]] || { echo "prompt file not found: $PROMPT_FILE" >&2; exit 64; }
mkdir -p "$OUT"
start="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
set +e
opencode run --format json --model "$MODEL" --agent "$AGENT" "$(cat "$PROMPT_FILE")" >"$OUT/opencode.ndjson" 2>"$OUT/opencode.stderr"
oc_status=$?
set -e
if [[ $oc_status -ne 0 ]]; then
  jq -n --arg attempt "$ATTEMPT" --arg base "$BASE" --arg started "$start" --arg ended "$(date -u +%Y-%m-%dT%H:%M:%SZ)" --argjson exit "$oc_status"     '{schema:1,attempt_id:$attempt,base_sha:$base,status:"opencode_failed",opencode_exit:$exit,started_at:$started,ended_at:$ended}' > "$OUT/evidence.json"
  exit "$oc_status"
fi
set +e
bash -euo pipefail -c "$VALIDATE" >"$OUT/validation.log" 2>&1
validation_status=$?
set -e
git diff --binary > "$OUT/worktree.diff"
git status --porcelain=v1 > "$OUT/status.txt"
jq -n --arg attempt "$ATTEMPT" --arg base "$BASE" --arg model "$MODEL" --arg agent "$AGENT" --arg started "$start" --arg ended "$(date -u +%Y-%m-%dT%H:%M:%SZ)" --argjson opencode_exit "$oc_status" --argjson validation_exit "$validation_status"   '{schema:1,attempt_id:$attempt,base_sha:$base,model:$model,agent:$agent,status:(if $validation_exit==0 then "validated" else "validation_failed" end),opencode_exit:$opencode_exit,validation_exit:$validation_exit,started_at:$started,ended_at:$ended}' > "$OUT/evidence.json"
[[ $validation_status -eq 0 ]]
