#!/usr/bin/env python3
"""Create or locate the pull request for a deterministic worker candidate."""

from __future__ import annotations

import argparse
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

API = os.environ.get("GITHUB_API_URL", "https://api.github.com")


def api(method: str, path: str, token: str, body: dict[str, Any] | None = None) -> Any:
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(
        f"{API}{path}",
        data=data,
        method=method,
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
        raise SystemExit(f"GitHub API {method} {path} failed: {exc.code} {payload}") from exc


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--repository", default=os.environ.get("GITHUB_REPOSITORY", ""))
    p.add_argument("--head", required=True)
    p.add_argument("--base", required=True)
    p.add_argument("--title", required=True)
    p.add_argument("--body", required=True)
    p.add_argument("--output")
    args = p.parse_args()

    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        raise SystemExit("GITHUB_TOKEN is required")
    owner, repo = args.repository.split("/", 1)

    query = urllib.parse.urlencode({"state": "open", "head": f"{owner}:{args.head}", "base": args.base})
    existing = api("GET", f"/repos/{owner}/{repo}/pulls?{query}", token)
    if existing:
        pr = existing[0]
    else:
        pr = api("POST", f"/repos/{owner}/{repo}/pulls", token, {
            "title": args.title,
            "head": args.head,
            "base": args.base,
            "body": args.body,
            "maintainer_can_modify": False,
        })

    values = {
        "pr_number": pr["number"],
        "pr_url": pr["html_url"],
        "pr_head_sha": pr["head"]["sha"],
    }
    if args.output:
        with open(args.output, "a", encoding="utf-8") as f:
            for key, value in values.items():
                f.write(f"{key}={value}\n")
    print(json.dumps(values, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
