#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
RELEASE_PATH = ROOT / "release.json"
IMPLEMENTATION_PLACEHOLDER = "__IMPLEMENTATION_SHA__"

# Files that change the distributed execution contract. release.json itself is
# intentionally excluded: a promotion commit records the already-built runtime
# without recursively making itself a new runtime.
RUNTIME_PATHS = (
    "VERSION",
    "Makefile",
    "action.yml",
    "admit/",
    "authorize/",
    "seal/",
    "scripts/",
    "templates/",
    "schemas/",
    "AGENTS.md",
    "CONTEXT.md",
    "docs/agents/",
    "opencode.json",
    ".opencode/",
    ".opencode-actions/",
)


class ReleaseError(RuntimeError):
    pass


def run_git(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if check and proc.returncode:
        raise ReleaseError(proc.stderr.strip() or proc.stdout.strip() or f"git {' '.join(args)} failed")
    return proc


def load_release() -> dict[str, Any]:
    try:
        doc = json.loads(RELEASE_PATH.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ReleaseError("release.json is missing") from exc
    except json.JSONDecodeError as exc:
        raise ReleaseError(f"release.json is invalid JSON: {exc}") from exc

    if doc.get("schema") != 1:
        raise ReleaseError("release.json schema must be 1")
    runtime = str(doc.get("runtime_sha", ""))
    if re.fullmatch(r"[0-9a-f]{40}", runtime) is None:
        raise ReleaseError("release runtime_sha must be a 40-character lowercase commit SHA")
    if not isinstance(doc.get("managed"), dict) or not doc["managed"]:
        raise ReleaseError("release.json managed map is empty")
    return doc


def write_release(doc: dict[str, Any]) -> None:
    RELEASE_PATH.write_text(json.dumps(doc, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def git_blob_oid(data: bytes) -> str:
    header = f"blob {len(data)}\0".encode()
    return hashlib.sha1(header + data).hexdigest()


def render_bytes(source_relative: str, release: dict[str, Any] | None = None) -> bytes:
    release = release or load_release()
    source = ROOT / source_relative
    raw = source.read_text(encoding="utf-8")
    rendered = raw.replace(IMPLEMENTATION_PLACEHOLDER, release["runtime_sha"])
    if IMPLEMENTATION_PLACEHOLDER in rendered:
        raise ReleaseError(f"unresolved implementation placeholder in {source_relative}")
    return rendered.encode()


def desired_managed_bytes(target_relative: str, release: dict[str, Any] | None = None) -> bytes:
    release = release or load_release()
    spec = release["managed"].get(target_relative)
    if not isinstance(spec, dict) or not spec.get("source"):
        raise ReleaseError(f"managed target missing from release.json: {target_relative}")
    return render_bytes(str(spec["source"]), release)


def accepted_previous_blobs(target_relative: str, release: dict[str, Any] | None = None) -> set[str]:
    release = release or load_release()
    spec = release["managed"].get(target_relative)
    if not isinstance(spec, dict):
        return set()
    values = spec.get("accepted_previous_blobs", [])
    if not isinstance(values, list):
        raise ReleaseError(f"accepted_previous_blobs must be a list for {target_relative}")
    return {str(value) for value in values}


def runtime_relevant(path: str) -> bool:
    for item in RUNTIME_PATHS:
        if item.endswith("/"):
            if path.startswith(item):
                return True
        elif path == item:
            return True
    return False


def changed_runtime_paths(base: str, head: str) -> list[str]:
    if run_git("merge-base", "--is-ancestor", base, head, check=False).returncode:
        raise ReleaseError(f"release runtime {base} is not an ancestor of {head}")
    proc = run_git("diff", "--name-only", f"{base}..{head}", "--")
    return sorted(path for path in proc.stdout.splitlines() if path and runtime_relevant(path))


def verify_action_refs(data: bytes, source: str, runtime_sha: str) -> None:
    text = data.decode()
    action_ref = re.compile(r"^\s*uses:\s*([^@\s]+)@([^\s#]+)", re.MULTILINE)
    for action, ref in action_ref.findall(text):
        if action.startswith("./"):
            continue
        if action.startswith("Samwise-x/opencode-actions"):
            if ref != runtime_sha:
                raise ReleaseError(f"{source}: self action ref {action}@{ref} != release runtime {runtime_sha}")
        elif re.fullmatch(r"[0-9a-f]{40}", ref) is None:
            raise ReleaseError(f"{source}: floating external action reference {action}@{ref}")


def verify() -> None:
    release = load_release()
    runtime = release["runtime_sha"]
    if run_git("cat-file", "-e", f"{runtime}^{{commit}}", check=False).returncode:
        raise ReleaseError(f"release runtime commit is not present in this checkout: {runtime}")

    version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    if release.get("version") != version:
        raise ReleaseError(f"release version {release.get('version')!r} does not match VERSION {version!r}")

    seen_sources: set[str] = set()
    for target, spec in sorted(release["managed"].items()):
        if not isinstance(spec, dict):
            raise ReleaseError(f"managed spec must be an object: {target}")
        source = str(spec.get("source", ""))
        if not source:
            raise ReleaseError(f"managed target has no source: {target}")
        if source in seen_sources:
            raise ReleaseError(f"managed source reused by multiple targets: {source}")
        seen_sources.add(source)
        data = desired_managed_bytes(target, release)
        verify_action_refs(data, source, runtime)
        for oid in accepted_previous_blobs(target, release):
            if re.fullmatch(r"[0-9a-f]{40}", oid) is None:
                raise ReleaseError(f"{target}: invalid legacy Git blob id {oid!r}")


def promote(runtime_sha: str) -> None:
    release = load_release()
    if re.fullmatch(r"[0-9a-f]{40}", runtime_sha) is None:
        raise ReleaseError("promotion runtime SHA must be a 40-character lowercase commit SHA")
    if run_git("cat-file", "-e", f"{runtime_sha}^{{commit}}", check=False).returncode:
        raise ReleaseError(f"promotion runtime commit is not present: {runtime_sha}")
    if run_git("merge-base", "--is-ancestor", release["runtime_sha"], runtime_sha, check=False).returncode:
        raise ReleaseError("promotion runtime must descend from the current release runtime")

    # Before switching the runtime identity, remember the exact generated bytes
    # from the prior release. Bootstrap may replace only one of these known
    # generated versions; unknown drift remains fail-closed.
    for target, spec in release["managed"].items():
        previous = git_blob_oid(desired_managed_bytes(target, release))
        accepted = [str(value) for value in spec.get("accepted_previous_blobs", [])]
        if previous not in accepted:
            accepted.append(previous)
        spec["accepted_previous_blobs"] = sorted(set(accepted))

    release["runtime_sha"] = runtime_sha
    release["version"] = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    write_release(release)
    verify()


def status(head: str) -> tuple[bool, list[str]]:
    release = load_release()
    changed = changed_runtime_paths(release["runtime_sha"], head)
    return bool(changed), changed


def emit_github_output(path: str | None, drift: bool, changed: list[str]) -> None:
    if not path:
        return
    with Path(path).open("a", encoding="utf-8") as handle:
        handle.write(f"drift={'true' if drift else 'false'}\n")
        handle.write(f"runtime_sha={load_release()['runtime_sha']}\n")
        handle.write("changed_paths<<EOF\n")
        handle.write("\n".join(changed) + "\n")
        handle.write("EOF\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("verify")

    status_parser = sub.add_parser("status")
    status_parser.add_argument("--head", default="HEAD")
    status_parser.add_argument("--github-output")

    promote_parser = sub.add_parser("promote")
    promote_parser.add_argument("--runtime-sha", required=True)

    render_parser = sub.add_parser("render")
    render_parser.add_argument("--target", required=True)
    render_parser.add_argument("--output", required=True)

    args = parser.parse_args()
    try:
        if args.command == "verify":
            verify()
            print("release contract verified")
            return 0
        if args.command == "status":
            drift, changed = status(args.head)
            emit_github_output(args.github_output, drift, changed)
            print(json.dumps({"drift": drift, "changed_paths": changed}, sort_keys=True))
            return 0
        if args.command == "promote":
            promote(args.runtime_sha)
            print(f"release promoted to {args.runtime_sha}")
            return 0
        if args.command == "render":
            Path(args.output).write_bytes(desired_managed_bytes(args.target))
            return 0
    except (OSError, json.JSONDecodeError, ReleaseError) as exc:
        print(f"release: {exc}", file=sys.stderr)
        return 2
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
