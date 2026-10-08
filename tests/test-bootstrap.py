#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import os
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENV = {**os.environ, "OPENCODE_BOOTSTRAP_TESTING": "1"}


def run_make(target: Path, *, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["make", "-f", str(ROOT / "Makefile"), f"TARGET={target}"],
        cwd=ROOT,
        env=ENV,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=check,
    )


def init_repo(path: Path) -> None:
    subprocess.run(["git", "init", "-q", "-b", "main", str(path)], check=True)
    subprocess.run(["git", "-C", str(path), "config", "user.name", "test"], check=True)
    subprocess.run(["git", "-C", str(path), "config", "user.email", "test@example.com"], check=True)


def snapshot(path: Path) -> dict[str, str]:
    result = {}
    for file in sorted(p for p in path.rglob("*") if p.is_file() and ".git" not in p.parts):
        result[str(file.relative_to(path))] = hashlib.sha256(file.read_bytes()).hexdigest()
    return result


with tempfile.TemporaryDirectory() as td:
    base = Path(td)

    green = base / "green"
    green.mkdir()
    init_repo(green)
    run_make(green)
    first = snapshot(green)
    run_make(green)
    assert snapshot(green) == first

    required = {
        ".github/workflows/opencode-frontier.yml",
        ".github/workflows/opencode-candidate-validation.yml",
        ".github/workflows/opencode-admit.yml",
        ".github/opencode/frontier.md",
        ".opencode-actions/protected-paths.txt",
        ".opencode/plugins/harden-runtime.js",
        "AGENTS.md",
        "CONTEXT.md",
        "flake.nix",
        "dagger.json",
        "dagger/main.go",
        "opencode.json",
    }
    assert required <= set(first)
    assert ".github/opencode/**" in (green / ".opencode-actions/protected-paths.txt").read_text()

    brown = base / "brown"
    brown.mkdir()
    init_repo(brown)
    originals = {
        "AGENTS.md": "# custom agents\n",
        "CONTEXT.md": "# Domain language\n\n**widget**: existing term.\n",
        "flake.nix": "{ outputs = _: {}; }\n",
        "dagger.json": '{"name":"existing","sdk":{"source":"go"}}\n',
        "dagger/main.go": "package main\n\ntype Existing struct{}\n",
    }
    for name, content in originals.items():
        path = brown / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    run_make(brown)
    for name, content in originals.items():
        assert (brown / name).read_text(encoding="utf-8") == content
    first = snapshot(brown)
    run_make(brown)
    assert snapshot(brown) == first

    conflict = base / "conflict"
    conflict.mkdir()
    init_repo(conflict)
    path = conflict / ".github/workflows/opencode-frontier.yml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("name: custom\n", encoding="utf-8")
    result = run_make(conflict, check=False)
    assert result.returncode != 0
    assert path.read_text(encoding="utf-8") == "name: custom\n"

print("bootstrap convergence tests passed")
