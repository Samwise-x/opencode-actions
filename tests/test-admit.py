#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SPEC=importlib.util.spec_from_file_location("admit",ROOT/"scripts/admit.py")
assert SPEC and SPEC.loader
admit=importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(admit)

owner="example"
repo="target"
candidate="b"*40
workflow=".github/workflows/opencode-candidate-validation.yml"
q={
    "validation_run_id":"456",
    "validation_workflow_ref":f"{owner}/{repo}/{workflow}@refs/pull/11/merge",
    "required_checks":["deterministic","security"],
}

run={
    "head_sha":candidate,
    "path":workflow,
    "event":"pull_request",
    "status":"completed",
    "conclusion":"success",
    "pull_requests":[{"number":11}],
}
jobs={"jobs":[
    {"name":"deterministic","status":"completed","conclusion":"success"},
    {"name":"security","status":"completed","conclusion":"success"},
]}

def install(run_doc=run,jobs_doc=jobs):
    def fake(method:str,path:str,token:str,body=None):
        assert method=="GET"
        if path.endswith("/actions/runs/456"):
            return run_doc
        if path.endswith("/actions/runs/456/jobs?per_page=100"):
            return jobs_doc
        raise AssertionError(path)
    admit.request=fake

install()
admit.verify_validation_run(owner,repo,"token",q,candidate,11,workflow,["deterministic","security"])

install({**run,"head_sha":"c"*40},jobs)
try:
    admit.verify_validation_run(owner,repo,"token",q,candidate,11,workflow,["deterministic","security"])
except SystemExit as exc:
    assert "head SHA" in str(exc)
else:
    raise AssertionError("moved validation head unexpectedly accepted")

install({**run,"path":".github/workflows/other.yml"},jobs)
try:
    admit.verify_validation_run(owner,repo,"token",q,candidate,11,workflow,["deterministic","security"])
except SystemExit as exc:
    assert "workflow path" in str(exc)
else:
    raise AssertionError("wrong workflow unexpectedly accepted")

install(run,{"jobs":[jobs["jobs"][0]]})
try:
    admit.verify_validation_run(owner,repo,"token",q,candidate,11,workflow,["deterministic","security"])
except SystemExit as exc:
    assert "security" in str(exc)
else:
    raise AssertionError("missing required job unexpectedly accepted")

install({**run,"pull_requests":[{"number":12}]},jobs)
try:
    admit.verify_validation_run(owner,repo,"token",q,candidate,11,workflow,["deterministic","security"])
except SystemExit as exc:
    assert "qualified PR" in str(exc)
else:
    raise AssertionError("wrong PR binding unexpectedly accepted")

install()
try:
    admit.verify_validation_run(owner,repo,"token",q,candidate,11,workflow,["deterministic"])
except SystemExit as exc:
    assert "required-check set" in str(exc)
else:
    raise AssertionError("qualification/check-set drift unexpectedly accepted")

print("admission exact-run tests passed")
