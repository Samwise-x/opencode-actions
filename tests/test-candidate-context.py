#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SPEC=importlib.util.spec_from_file_location("candidate_context",ROOT/"scripts/candidate-context.py")
assert SPEC and SPEC.loader
context=importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(context)

repo="example/repo"
sha="b"*40

context.commit_message=lambda repository,candidate: "human change"
human=context.classify(repo,12,sha,"main")
assert human["agent_candidate"]=="false"
assert human["authorized"]=="true"

message="subject\n\nOpenCode-Attempt: 123-1\nOpenCode-Issue: #7"
context.commit_message=lambda repository,candidate: message

pull={
    "state":"OPEN",
    "baseRefName":"main",
    "headRefOid":sha,
    "closingIssuesReferences":[{"number":7,"url":"https://github.com/example/repo/issues/7"}],
}
ready={"number":7,"state":"OPEN","labels":[{"name":"ready-for-agent"}]}

def fake_ready(*args:str):
    if args[:2]==("pr","view"): return pull
    if args[:2]==("issue","view"): return ready
    raise AssertionError(args)

context.gh=fake_ready
authorized=context.classify(repo,12,sha,"main")
assert authorized["agent_candidate"]=="true"
assert authorized["authorized"]=="true"
assert authorized["issue_number"]=="7"
assert authorized["attempt_id"]=="123-1"

unready={"number":7,"state":"OPEN","labels":[{"name":"ready-for-human"}]}
def fake_unready(*args:str):
    if args[:2]==("pr","view"): return pull
    if args[:2]==("issue","view"): return unready
    raise AssertionError(args)

context.gh=fake_unready
blocked=context.classify(repo,12,sha,"main")
assert blocked["authorized"]=="false"
assert blocked["reason"]=="issue_not_ready_for_agent"

moved={**pull,"headRefOid":"c"*40}
def fake_moved(*args:str):
    if args[:2]==("pr","view"): return moved
    raise AssertionError(args)

context.gh=fake_moved
stale=context.classify(repo,12,sha,"main")
assert stale["authorized"]=="false"
assert stale["reason"]=="pull_request_head_moved"

context.commit_message=lambda repository,candidate: "OpenCode-Attempt: 123-1"
partial=context.classify(repo,12,sha,"main")
assert partial["agent_candidate"]=="true"
assert partial["authorized"]=="false"
assert partial["reason"]=="incomplete_opencode_commit_identity"

print("candidate-context tests passed")
