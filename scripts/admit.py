#!/usr/bin/env python3
"""Model-free protected-PR admission for an exact validated candidate."""

from __future__ import annotations
import argparse, json, os, sys, urllib.error, urllib.request
from pathlib import Path
from typing import Any

API = os.environ.get("GITHUB_API_URL", "https://api.github.com")

def request(method: str, path: str, token: str, body: dict[str, Any] | None = None) -> Any:
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(
        f"{API}{path}", data=data, method=method,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "Samwise-x/opencode-actions",
            **({"Content-Type": "application/json"} if data is not None else {}),
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            payload = response.read()
            return json.loads(payload) if payload else {}
    except urllib.error.HTTPError as exc:
        payload = exc.read().decode(errors="replace")
        raise RuntimeError(f"GitHub API {method} {path} failed: {exc.code} {payload}") from exc

def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--repository", default=os.environ.get("GITHUB_REPOSITORY", ""))
    p.add_argument("--pr", type=int, required=True)
    p.add_argument("--candidate-sha", required=True)
    p.add_argument("--evidence", required=True)
    p.add_argument("--required-check", action="append", default=[])
    p.add_argument("--merge-method", choices=("merge", "squash", "rebase"), default="squash")
    args = p.parse_args()

    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        raise SystemExit("GITHUB_TOKEN is required")
    if "/" not in args.repository:
        raise SystemExit("--repository must be owner/name")

    evidence = json.loads(Path(args.evidence).read_text(encoding="utf-8"))
    if evidence.get("schema") != 1:
        raise SystemExit("unsupported evidence schema")
    if evidence.get("candidate_sha") != args.candidate_sha:
        raise SystemExit("evidence candidate SHA does not match requested candidate")
    if evidence.get("status") != "validated":
        raise SystemExit("candidate evidence is not validated")
    if int(evidence.get("opencode_exit", 1)) != 0 or int(evidence.get("validation_exit", 1)) != 0:
        raise SystemExit("execution or deterministic validation failed")

    owner, repo = args.repository.split("/", 1)
    pr = request("GET", f"/repos/{owner}/{repo}/pulls/{args.pr}", token)
    if pr.get("state") != "open":
        raise SystemExit("PR is not open")
    if pr.get("head", {}).get("sha") != args.candidate_sha:
        raise SystemExit("PR head changed after evidence was produced")

    base_ref = pr.get("base", {}).get("ref")
    if not base_ref:
        raise SystemExit("PR has no base ref")
    base = request("GET", f"/repos/{owner}/{repo}/git/ref/heads/{base_ref}", token)
    current_base_sha = base.get("object", {}).get("sha")
    if current_base_sha != evidence.get("base_sha"):
        raise SystemExit(
            f"canonical base moved: evidence={evidence.get('base_sha')} current={current_base_sha}; reconstruct"
        )

    checks = request("GET", f"/repos/{owner}/{repo}/commits/{args.candidate_sha}/check-runs?per_page=100", token)
    by_name: dict[str, list[dict[str, Any]]] = {}
    for check in checks.get("check_runs", []):
        by_name.setdefault(check.get("name", ""), []).append(check)
    for required in args.required_check:
        runs = by_name.get(required, [])
        if not runs:
            raise SystemExit(f"required check missing: {required}")
        latest = max(runs, key=lambda x: x.get("completed_at") or x.get("started_at") or "")
        if latest.get("status") != "completed" or latest.get("conclusion") != "success":
            raise SystemExit(
                f"required check not successful: {required}: {latest.get('status')}/{latest.get('conclusion')}"
            )

    result = request(
        "PUT", f"/repos/{owner}/{repo}/pulls/{args.pr}/merge", token,
        {
            "sha": args.candidate_sha,
            "merge_method": args.merge_method,
            "commit_title": f"admit: PR #{args.pr} @ {args.candidate_sha[:12]}",
        },
    )
    if not result.get("merged"):
        raise SystemExit(f"GitHub refused admission: {result.get('message', 'unknown reason')}")
    print(json.dumps({
        "admitted": True,
        "candidate_sha": args.candidate_sha,
        "merge_sha": result.get("sha", ""),
        "pr": args.pr,
    }, sort_keys=True))
    return 0

if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1)
