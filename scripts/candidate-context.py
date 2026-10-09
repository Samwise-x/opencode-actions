#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any


def gh(*args: str) -> Any:
    proc = subprocess.run(
        ["/usr/bin/gh", *args],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return json.loads(proc.stdout or "null")


def commit_message(repository: str, sha: str) -> str:
    return str(
        gh(
            "api",
            f"repos/{repository}/commits/{sha}",
            "--jq",
            ".commit.message",
        )
    )


def trailers(message: str) -> tuple[str | None, int | None]:
    attempt_matches = re.findall(r"^OpenCode-Attempt:\s*(\S+)\s*$", message, flags=re.MULTILINE)
    issue_matches = re.findall(r"^OpenCode-Issue:\s*#?(\d+)\s*$", message, flags=re.MULTILINE)
    attempt = attempt_matches[-1] if attempt_matches else None
    issue = int(issue_matches[-1]) if issue_matches else None
    return attempt, issue


def labels(issue: dict[str, Any]) -> set[str]:
    return {str(item.get("name", "")).lower() for item in issue.get("labels", [])}


def linked_issue_numbers(repository: str, pull: dict[str, Any]) -> set[int]:
    result: set[int] = set()
    for item in pull.get("closingIssuesReferences", []):
        url = str(item.get("url", ""))
        if url and f"github.com/{repository}/issues/" not in url:
            continue
        if item.get("number") is not None:
            result.add(int(item["number"]))
    return result


def classify(repository: str, pr_number: int, candidate_sha: str, base: str) -> dict[str, str]:
    message = commit_message(repository, candidate_sha)
    attempt, issue_number = trailers(message)

    if attempt is None and issue_number is None:
        return {
            "agent_candidate": "false",
            "authorized": "true",
            "reason": "human_or_non_agent_candidate",
            "attempt_id": "",
            "issue_number": "",
        }

    if attempt is None or issue_number is None:
        return {
            "agent_candidate": "true",
            "authorized": "false",
            "reason": "incomplete_opencode_commit_identity",
            "attempt_id": attempt or "",
            "issue_number": str(issue_number or ""),
        }

    pull = gh(
        "pr",
        "view",
        str(pr_number),
        "--repo",
        repository,
        "--json",
        "number,state,baseRefName,headRefOid,closingIssuesReferences",
    )
    if pull.get("state") != "OPEN":
        reason = "pull_request_not_open"
    elif pull.get("baseRefName") != base:
        reason = "pull_request_targets_wrong_base"
    elif pull.get("headRefOid") != candidate_sha:
        reason = "pull_request_head_moved"
    elif issue_number not in linked_issue_numbers(repository, pull):
        reason = "native_issue_link_missing"
    else:
        issue = gh(
            "issue",
            "view",
            str(issue_number),
            "--repo",
            repository,
            "--json",
            "number,state,labels",
        )
        if issue.get("state") != "OPEN":
            reason = "issue_not_open"
        elif "ready-for-agent" not in labels(issue):
            reason = "issue_not_ready_for_agent"
        else:
            return {
                "agent_candidate": "true",
                "authorized": "true",
                "reason": "authorized",
                "attempt_id": attempt,
                "issue_number": str(issue_number),
            }

    return {
        "agent_candidate": "true",
        "authorized": "false",
        "reason": reason,
        "attempt_id": attempt,
        "issue_number": str(issue_number),
    }


def emit(path: Path, values: dict[str, str]) -> None:
    with path.open("a", encoding="utf-8") as handle:
        for key, value in values.items():
            handle.write(f"{key}={value}\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository", default=os.environ.get("GITHUB_REPOSITORY", ""))
    parser.add_argument("--pr", type=int, required=True)
    parser.add_argument("--candidate-sha", required=True)
    parser.add_argument("--base", required=True)
    parser.add_argument("--github-output", required=True)
    args = parser.parse_args()

    if not args.repository or "/" not in args.repository:
        print("candidate-context: repository must be owner/name", file=sys.stderr)
        return 2
    if re.fullmatch(r"[0-9a-f]{40}", args.candidate_sha) is None:
        print("candidate-context: candidate SHA must be a full commit SHA", file=sys.stderr)
        return 2

    try:
        values = classify(args.repository, args.pr, args.candidate_sha, args.base)
    except subprocess.CalledProcessError as exc:
        print(exc.stderr or str(exc), file=sys.stderr)
        return 1

    emit(Path(args.github_output), values)
    print(json.dumps(values, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
