#!/usr/bin/env python3
"""Git-backed single-writer trajectory ledger.

The ledger is one JSON blob committed to a dedicated ref. Every state transition
is a fast-forward push from the exact ref head that was read. A competing writer
therefore loses rather than silently overwriting newer state.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
import uuid
from datetime import datetime, timezone
from typing import Any


def run(*args: str, input_text: str | None = None, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        input=input_text,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=check,
    )


def now_epoch() -> int:
    return int(time.time())


def iso(ts: int | None = None) -> str:
    return datetime.fromtimestamp(ts or now_epoch(), timezone.utc).isoformat()


def ref_branch(ref: str) -> str:
    prefix = "refs/heads/"
    if not ref.startswith(prefix):
        raise SystemExit("trajectory ref must be under refs/heads/")
    return ref[len(prefix):]


def fetch_head(ref: str) -> str | None:
    result = run("fetch", "--quiet", "--no-tags", "origin", f"{ref}:refs/remotes/origin/{ref_branch(ref)}", check=False)
    remote = f"refs/remotes/origin/{ref_branch(ref)}"
    probe = run("rev-parse", "--verify", remote, check=False)
    if probe.returncode != 0:
        return None
    return probe.stdout.strip()


def read_state(commit: str | None) -> dict[str, Any]:
    if not commit:
        return {
            "schema": "opencode-actions/trajectory/v1",
            "epoch": 0,
            "status": "idle",
        }
    result = run("show", f"{commit}:trajectory.json", check=False)
    if result.returncode != 0:
        raise RuntimeError(f"trajectory ref {commit} has no trajectory.json")
    state = json.loads(result.stdout)
    if state.get("schema") != "opencode-actions/trajectory/v1":
        raise RuntimeError("unsupported trajectory schema")
    return state


def make_commit(state: dict[str, Any], parent: str | None, message: str) -> str:
    body = json.dumps(state, indent=2, sort_keys=True) + "\n"
    blob = run("hash-object", "-w", "--stdin", input_text=body).stdout.strip()
    tree_line = f"100644 blob {blob}\ttrajectory.json\n"
    tree = run("mktree", input_text=tree_line).stdout.strip()

    env = os.environ.copy()
    env.setdefault("GIT_AUTHOR_NAME", "opencode-actions")
    env.setdefault("GIT_AUTHOR_EMAIL", "opencode-actions@users.noreply.github.com")
    env.setdefault("GIT_COMMITTER_NAME", env["GIT_AUTHOR_NAME"])
    env.setdefault("GIT_COMMITTER_EMAIL", env["GIT_AUTHOR_EMAIL"])

    cmd = ["git", "commit-tree", tree, "-m", message]
    if parent:
        cmd.extend(["-p", parent])
    result = subprocess.run(cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env, check=True)
    return result.stdout.strip()


def push_transition(commit: str, ref: str) -> bool:
    result = run("push", "--porcelain", "origin", f"{commit}:{ref}", check=False)
    if result.returncode == 0:
        return True
    sys.stderr.write(result.stdout)
    sys.stderr.write(result.stderr)
    return False


def write_output(path: str | None, values: dict[str, Any]) -> None:
    lines = [f"{key}={str(value).lower() if isinstance(value, bool) else value}\n" for key, value in values.items()]
    if path:
        with open(path, "a", encoding="utf-8") as f:
            f.writelines(lines)
    else:
        sys.stdout.writelines(lines)


def acquire(args: argparse.Namespace) -> int:
    lease_seconds = args.lease_seconds
    if lease_seconds < 60:
        raise SystemExit("lease must be at least 60 seconds")

    for _ in range(8):
        head = fetch_head(args.ref)
        state = read_state(head)
        now = now_epoch()

        active = state.get("status") == "active"
        expires = int(state.get("lease_expires_epoch", 0) or 0)
        if active and expires > now:
            write_output(args.output, {
                "acquired": False,
                "attempt_id": state.get("attempt_id", ""),
                "epoch": state.get("epoch", 0),
                "base_sha": state.get("base_sha", ""),
                "lease_expires_epoch": expires,
            })
            return 0

        epoch = int(state.get("epoch", 0)) + 1
        attempt = f"{os.environ.get('GITHUB_RUN_ID', 'local')}-{os.environ.get('GITHUB_RUN_ATTEMPT', '1')}-{uuid.uuid4().hex[:12]}"
        next_state = {
            "schema": "opencode-actions/trajectory/v1",
            "epoch": epoch,
            "status": "active",
            "attempt_id": attempt,
            "base_sha": args.canonical_sha,
            "candidate_sha": "",
            "acquired_at": iso(now),
            "lease_expires_epoch": now + lease_seconds,
            "lease_expires_at": iso(now + lease_seconds),
            "github": {
                "repository": os.environ.get("GITHUB_REPOSITORY", ""),
                "run_id": os.environ.get("GITHUB_RUN_ID", ""),
                "run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT", ""),
                "workflow_ref": os.environ.get("GITHUB_WORKFLOW_REF", ""),
            },
            "evidence": {},
            "previous": {
                "epoch": state.get("epoch", 0),
                "status": state.get("status", "idle"),
                "attempt_id": state.get("attempt_id", ""),
                "candidate_sha": state.get("candidate_sha", ""),
            },
        }
        commit = make_commit(next_state, head, f"trajectory: acquire epoch {epoch} ({attempt})")
        if push_transition(commit, args.ref):
            write_output(args.output, {
                "acquired": True,
                "attempt_id": attempt,
                "epoch": epoch,
                "base_sha": args.canonical_sha,
                "lease_expires_epoch": now + lease_seconds,
            })
            return 0

        time.sleep(1)

    raise RuntimeError("failed to acquire trajectory after concurrent updates")


def finalize(args: argparse.Namespace) -> int:
    head = fetch_head(args.ref)
    if not head:
        raise RuntimeError("trajectory ref does not exist")
    state = read_state(head)

    if state.get("attempt_id") != args.attempt_id or int(state.get("epoch", -1)) != args.epoch:
        raise RuntimeError("stale worker: trajectory ownership changed before finalize")
    if state.get("status") != "active":
        raise RuntimeError(f"cannot finalize trajectory in state {state.get('status')!r}")

    next_state = dict(state)
    next_state.update({
        "status": args.status,
        "candidate_sha": args.candidate_sha,
        "finalized_at": iso(),
        "lease_expires_epoch": 0,
        "lease_expires_at": "",
        "evidence": {
            "artifact": f"opencode-evidence-{args.attempt_id}",
            "path": args.evidence_path,
            "run_id": os.environ.get("GITHUB_RUN_ID", ""),
        },
    })

    commit = make_commit(next_state, head, f"trajectory: finalize epoch {args.epoch} ({args.status})")
    if not push_transition(commit, args.ref):
        raise RuntimeError("stale worker: trajectory changed during finalize")
    return 0


def status(args: argparse.Namespace) -> int:
    head = fetch_head(args.ref)
    print(json.dumps(read_state(head), indent=2, sort_keys=True))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("acquire")
    p.add_argument("--ref", required=True)
    p.add_argument("--lease-seconds", type=int, required=True)
    p.add_argument("--canonical-sha", required=True)
    p.add_argument("--output")
    p.set_defaults(func=acquire)

    p = sub.add_parser("finalize")
    p.add_argument("--ref", required=True)
    p.add_argument("--attempt-id", required=True)
    p.add_argument("--epoch", type=int, required=True)
    p.add_argument("--candidate-sha", default="")
    p.add_argument("--status", choices=("executed", "failed", "validated", "admitted"), required=True)
    p.add_argument("--evidence-path", default="")
    p.set_defaults(func=finalize)

    p = sub.add_parser("status")
    p.add_argument("--ref", required=True)
    p.set_defaults(func=status)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
