#!/usr/bin/env python3
from __future__ import annotations
import json
import os
import subprocess
import tempfile
from pathlib import Path

root = Path(__file__).resolve().parents[1]

with tempfile.TemporaryDirectory() as td:
    td = Path(td)
    evidence = {
        "schema": 2,
        "kind": "agent-attempt",
        "attempt_id": "123-1",
        "issue_number": 7,
        "base_sha": "a" * 40,
        "candidate_sha": "b" * 40,
        "candidate_branch": "opencode/issue-7",
        "pr_number": 11,
        "model": "provider/model",
        "agent": "build",
        "status": "prevalidated",
        "opencode_exit": 0,
        "validation_exit": 0,
        "started_at": "2026-01-01T00:00:00+00:00",
        "ended_at": "2026-01-01T00:01:00+00:00"
    }
    source = td / "evidence.json"
    out = td / "qualification.json"
    source.write_text(json.dumps(evidence), encoding="utf-8")

    env = os.environ.copy()
    env.update({
        "GITHUB_REPOSITORY": "owner/repo",
        "GITHUB_RUN_ID": "456",
        "GITHUB_WORKFLOW_REF": "owner/repo/.github/workflows/opencode-candidate-validation.yml@refs/pull/11/merge",
    })
    subprocess.run([
        "python3", str(root / "scripts/seal.py"),
        "--frontier-evidence", str(source),
        "--candidate", "b" * 40,
        "--pr", "11",
        "--required-check", "deterministic",
        "--required-check", "security",
        "--output", str(out),
    ], check=True, env=env)

    result = json.loads(out.read_text(encoding="utf-8"))
    assert result["kind"] == "qualified-candidate"
    assert result["candidate_sha"] == "b" * 40
    assert result["base_sha"] == "a" * 40
    assert result["required_checks"] == ["deterministic", "security"]
    assert result["validation_run_id"] == "456"

print("seal tests passed")
