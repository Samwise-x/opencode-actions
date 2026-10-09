#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SPEC=importlib.util.spec_from_file_location("release_contract",ROOT/"scripts/release.py")
assert SPEC and SPEC.loader
release=importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(release)

doc=release.load_release()
release.verify()

for target,spec in doc["managed"].items():
    rendered=release.desired_managed_bytes(target,doc)
    assert release.IMPLEMENTATION_PLACEHOLDER.encode() not in rendered
    assert spec["source"]

legacy=subprocess.run(
    [
        "git","show",
        "cc756af107155d4dc861e4a660674765de4b16ca:templates/frontier.yml",
    ],
    cwd=ROOT,
    check=True,
    stdout=subprocess.PIPE,
).stdout
legacy_oid=release.git_blob_oid(legacy)
assert legacy_oid in release.accepted_previous_blobs(
    ".github/workflows/opencode-frontier.yml",doc
)

drift,changed=release.status("HEAD")
assert not drift,changed
assert changed==[]

print("release identity tests passed")
