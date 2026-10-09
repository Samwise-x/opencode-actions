#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
CHECK=ROOT/"scripts/schema-check.py"

def run(schema:str,doc:dict,ok:bool=True)->None:
    with tempfile.TemporaryDirectory() as td:
        path=Path(td)/"doc.json"
        path.write_text(json.dumps(doc),encoding="utf-8")
        proc=subprocess.run(
            ["python3",str(CHECK),str(ROOT/"schemas"/schema),str(path)],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        if ok:
            assert proc.returncode==0,proc.stderr
        else:
            assert proc.returncode!=0

evidence={
    "schema":2,
    "kind":"agent-attempt",
    "attempt_id":"123-1",
    "base_sha":"a"*40,
    "model":"provider/model",
    "agent":"build",
    "status":"opencode_failed",
    "opencode_exit":1,
    "started_at":"2026-10-09T00:00:00+00:00",
    "ended_at":"2026-10-09T00:01:00+00:00",
}
run("evidence-v2.schema.json",evidence)
run("evidence-v2.schema.json",{**evidence,"base_sha":"not-a-sha"},ok=False)

qualification={
    "schema":1,
    "kind":"qualified-candidate",
    "repository":"owner/repo",
    "candidate_sha":"b"*40,
    "base_sha":"a"*40,
    "issue_number":7,
    "pr_number":11,
    "attempt_id":"123-1",
    "frontier_evidence_sha256":"c"*64,
    "validation_run_id":"456",
    "validation_workflow_ref":"owner/repo/.github/workflows/opencode-candidate-validation.yml@refs/pull/11/merge",
    "required_checks":["deterministic","security"],
    "generated_at":"2026-10-09T00:01:00+00:00",
}
run("qualification-v1.schema.json",qualification)
run("qualification-v1.schema.json",{**qualification,"surprise":True},ok=False)

trajectory={
    "schema":2,
    "version":1,
    "status":"leased",
    "lease":{
        "token":"d"*64,
        "attempt":"123-1",
        "base_sha":"a"*40,
        "run_id":"123",
        "expires_epoch":9999999999,
    },
    "last_attempt":"123-1",
    "last_base":None,
    "last_candidate":None,
    "last_evidence":None,
    "last_issue":None,
    "last_pr":None,
}
run("trajectory-v2.schema.json",trajectory)
bad={**trajectory,"lease":{**trajectory["lease"],"expires_epoch":-1}}
run("trajectory-v2.schema.json",bad,ok=False)

print("schema contract tests passed")
