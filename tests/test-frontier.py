#!/usr/bin/env python3
from __future__ import annotations
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]
SPEC=importlib.util.spec_from_file_location("select_frontier",ROOT/"scripts/select-frontier.py")
assert SPEC and SPEC.loader
frontier=importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(frontier)

os.environ["GITHUB_REPOSITORY"]="Samwise-x/opencode-actions"

def issue_doc(number:int,title:str)->dict:
    return {"number":number,"title":title,"body":"","url":f"https://github.com/Samwise-x/opencode-actions/issues/{number}",
            "state":"OPEN","labels":[{"name":"ready-for-agent"}],"comments":[]}

def pr_doc(number:int,head:str)->dict:
    return {"number":number,"title":"candidate","body":"","url":f"https://github.com/Samwise-x/opencode-actions/pull/{number}",
            "state":"OPEN","baseRefName":"main","headRefName":head,"headRefOid":"deadbeef","comments":[],"reviews":[]}

def run(prs:list[dict],ready:list[dict],issues:dict[int,dict],pulls:dict[int,dict],explicit:str="")->dict:
    def fake(*args:str):
        if args[:2]==("pr","list"): return prs
        if args[:2]==("pr","view"): return pulls[int(args[2])]
        if args[:2]==("issue","view"): return issues[int(args[2])]
        if args[:2]==("issue","list"): return ready
        raise AssertionError(args)

    frontier.gh=fake
    old=sys.argv
    try:
        with tempfile.TemporaryDirectory() as td:
            out=Path(td)/"frontier.json"
            sys.argv=["select-frontier.py","--base","main","--output",str(out)]
            if explicit: sys.argv += ["--issue",explicit]
            assert frontier.main()==0
            return json.loads(out.read_text())
    finally:
        sys.argv=old

issue5=issue_doc(5,"protocol")
issue7=issue_doc(7,"fresh")
noncanonical={
    "number":6,
    "headRefName":"implementation/agent-protocol-v1",
    "createdAt":"2026-10-08T02:24:30Z",
    "closingIssuesReferences":[{"number":5,"url":issue5["url"]}],
}
ready=[
    {"number":5,"title":"protocol","url":issue5["url"],"createdAt":"2026-10-08T02:18:41Z","labels":[{"name":"ready-for-agent"}]},
    {"number":7,"title":"fresh","url":issue7["url"],"createdAt":"2026-10-08T06:15:14Z","labels":[{"name":"ready-for-agent"}]},
]
doc=run([noncanonical],ready,{5:issue5,7:issue7},{6:pr_doc(6,"implementation/agent-protocol-v1")})
assert doc["issue"]["number"]==5
assert doc["branch"]=="implementation/agent-protocol-v1"
assert doc["pr"]["number"]==6

doc=run([noncanonical],ready,{5:issue5,7:issue7},{6:pr_doc(6,"implementation/agent-protocol-v1")},"5")
assert doc["branch"]=="implementation/agent-protocol-v1"

issue8=issue_doc(8,"canonical")
canonical={
    "number":8,
    "headRefName":"opencode/issue-8",
    "createdAt":"2026-10-08T07:00:00Z",
    "closingIssuesReferences":[{"number":8,"url":issue8["url"]}],
}
doc=run([canonical],[],{8:issue8},{8:pr_doc(8,"opencode/issue-8")})
assert doc["issue"]["number"]==8
assert doc["branch"]=="opencode/issue-8"

print("frontier reconstruction tests passed")
