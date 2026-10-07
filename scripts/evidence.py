#!/usr/bin/env python3
"""Create deterministic evidence manifests for disposable OpenCode executions."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path


def sha256(path: str) -> str:
    p = Path(path)
    if not p.exists():
        return ""
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], text=True).strip()


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    create = sub.add_parser("create")
    create.add_argument("--output", required=True)
    create.add_argument("--attempt-id", required=True)
    create.add_argument("--epoch", required=True, type=int)
    create.add_argument("--base-sha", required=True)
    create.add_argument("--candidate-sha", required=True)
    create.add_argument("--exit-code", required=True, type=int)
    create.add_argument("--dirty", required=True, choices=("true", "false"))
    create.add_argument("--model", required=True)
    create.add_argument("--agent", required=True)
    create.add_argument("--events", required=True)
    create.add_argument("--stdout", required=True)
    create.add_argument("--stderr", required=True)
    create.add_argument("--pr-number", default="")
    create.add_argument("--pr-url", default="")
    args = parser.parse_args()

    if args.command != "create":
        return 2

    manifest = {
        "schema": "opencode-actions/evidence/v1",
        "attempt_id": args.attempt_id,
        "trajectory_epoch": args.epoch,
        "repository": os.environ.get("GITHUB_REPOSITORY", ""),
        "workflow": {
            "run_id": os.environ.get("GITHUB_RUN_ID", ""),
            "run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT", ""),
            "job": os.environ.get("GITHUB_JOB", ""),
            "workflow_ref": os.environ.get("GITHUB_WORKFLOW_REF", ""),
            "server_url": os.environ.get("GITHUB_SERVER_URL", "https://github.com"),
        },
        "git": {
            "base_sha": args.base_sha,
            "candidate_sha": args.candidate_sha,
            "head_ref": os.environ.get("GITHUB_HEAD_REF", ""),
            "ref": os.environ.get("GITHUB_REF", ""),
            "dirty": args.dirty == "true",
            "tree_sha": git("rev-parse", f"{args.candidate_sha}^{{tree}}"),
            "pr_number": args.pr_number,
            "pr_url": args.pr_url,
        },
        "execution": {
            "model": args.model,
            "agent": args.agent,
            "exit_code": args.exit_code,
            "opencode_version": "1.18.35",
        },
        "artifacts": {
            "events": {"path": args.events, "sha256": sha256(args.events)},
            "stdout": {"path": args.stdout, "sha256": sha256(args.stdout)},
            "stderr": {"path": args.stderr, "sha256": sha256(args.stderr)},
        },
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
