#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, os, subprocess
from datetime import datetime
from pathlib import Path

def gh(*args: str):
    p = subprocess.run(["/usr/bin/gh", *args], check=True, text=True, capture_output=True)
    return json.loads(p.stdout or "null")

def when(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))

def label_names(item: dict) -> set[str]:
    return {str(x.get("name", "")).lower() for x in item.get("labels", [])}

def ready(item: dict) -> bool:
    return item.get("state") == "OPEN" and "ready-for-agent" in label_names(item)

def rank(labels: list[dict]) -> int:
    names = {str(x.get("name", "")).lower() for x in labels}
    order = {"priority:p0":0,"priority:critical":0,"priority:p1":1,"priority:high":1,
             "priority:p2":2,"priority:medium":2,"priority:p3":3,"priority:low":3}
    values = [value for name, value in order.items() if name in names]
    return min(values) if values else 100

def issue(number: int):
    return gh("issue","view",str(number),"--json","number,title,body,url,state,labels,comments")

def pr(number: int):
    return gh("pr","view",str(number),"--json",
              "number,title,body,url,state,baseRefName,headRefName,headRefOid,comments,reviews")

def linked_issue_numbers(item: dict) -> list[int]:
    repo=os.environ.get("GITHUB_REPOSITORY","")
    numbers=[]
    for ref in item.get("closingIssuesReferences",[]):
        url=str(ref.get("url",""))
        if repo and url and f"github.com/{repo}/issues/" not in url:
            continue
        if ref.get("number") is not None:
            numbers.append(int(ref["number"]))
    return numbers

def emit(out: Path, gh_out: Path | None, doc: dict) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, indent=2, sort_keys=True)+"\n", encoding="utf-8")
    if gh_out:
        with gh_out.open("a", encoding="utf-8") as f:
            f.write(f"status={doc['status']}\n")
            if doc["status"] == "work":
                f.write(f"issue_number={doc['issue']['number']}\n")
                f.write(f"issue_title={doc['issue']['title']}\n")
                f.write(f"branch={doc['branch']}\n")
                f.write(f"pr_number={doc['pr']['number'] if doc.get('pr') else ''}\n")

def main() -> int:
    p=argparse.ArgumentParser()
    p.add_argument("--base",default="main"); p.add_argument("--branch-prefix",default="opencode/issue-")
    p.add_argument("--issue",default=""); p.add_argument("--output",required=True); p.add_argument("--github-output")
    a=p.parse_args(); out=Path(a.output); gh_out=Path(a.github_output) if a.github_output else None

    prs=gh("pr","list","--state","open","--base",a.base,"--limit","100",
           "--json","number,headRefName,createdAt,closingIssuesReferences")

    if a.issue:
        n=int(a.issue); i=issue(n)
        if not ready(i):
            raise SystemExit(f"explicit issue #{n} is not authorized by ready-for-agent")
        linked=[item for item in prs if n in linked_issue_numbers(item)]
        if linked:
            item=min(linked,key=lambda x:(when(x["createdAt"]),int(x["number"])))
            pull=pr(item["number"])
            emit(out,gh_out,{"status":"work","issue":i,"branch":pull["headRefName"],"pr":pull})
        else:
            branch=f"{a.branch_prefix}{n}"
            emit(out,gh_out,{"status":"work","issue":i,"branch":branch,"pr":None})
        return 0

    active=[]
    for item in prs:
        for n in linked_issue_numbers(item):
            i=issue(n)
            if ready(i):
                active.append((when(item["createdAt"]),int(item["number"]),n,i,pr(item["number"])))
    if active:
        _,_,_,i,pull=min(active,key=lambda x:(x[0],x[1],x[2]))
        emit(out,gh_out,{"status":"work","issue":i,"branch":pull["headRefName"],"pr":pull}); return 0

    issues=gh("issue","list","--state","open","--label","ready-for-agent","--limit","100",
              "--json","number,title,url,createdAt,labels")
    if not issues: emit(out,gh_out,{"status":"idle"}); return 0
    issues.sort(key=lambda x:(rank(x.get("labels",[])),when(x["createdAt"]),int(x["number"])))
    i=issue(int(issues[0]["number"]))
    if not ready(i):
        raise SystemExit(f"ready-for-agent listing returned unauthorized issue #{i['number']}")
    emit(out,gh_out,{"status":"work","issue":i,"branch":f"{a.branch_prefix}{i['number']}","pr":None}); return 0

if __name__=="__main__": raise SystemExit(main())
