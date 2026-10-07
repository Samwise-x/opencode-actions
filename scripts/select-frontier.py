#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, re, subprocess
from datetime import datetime
from pathlib import Path

def gh(*args: str):
    p = subprocess.run(["/usr/bin/gh", *args], check=True, text=True, capture_output=True)
    return json.loads(p.stdout or "null")

def when(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))

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

    if a.issue:
        n=int(a.issue); i=issue(n)
        if i["state"]!="OPEN": raise SystemExit(f"explicit issue #{n} is not open")
        branch=f"{a.branch_prefix}{n}"
        prs=gh("pr","list","--state","open","--base",a.base,"--head",branch,"--limit","10","--json","number,createdAt")
        emit(out,gh_out,{"status":"work","issue":i,"branch":branch,"pr":pr(prs[0]["number"]) if prs else None}); return 0

    rx=re.compile(r"^"+re.escape(a.branch_prefix)+r"(\d+)$")
    prs=gh("pr","list","--state","open","--base",a.base,"--limit","100","--json","number,headRefName,createdAt")
    active=[]
    for item in prs:
        m=rx.match(item["headRefName"])
        if not m: continue
        i=issue(int(m.group(1)))
        if i["state"]=="OPEN": active.append((when(item["createdAt"]),int(item["number"]),i,pr(item["number"])))
    if active:
        _,_,i,pull=sorted(active,key=lambda x:(x[0],x[1]))[0]
        emit(out,gh_out,{"status":"work","issue":i,"branch":pull["headRefName"],"pr":pull}); return 0

    issues=gh("issue","list","--state","open","--label","ready-for-agent","--limit","100",
              "--json","number,title,url,createdAt,labels")
    if not issues: emit(out,gh_out,{"status":"idle"}); return 0
    issues.sort(key=lambda x:(rank(x.get("labels",[])),when(x["createdAt"]),int(x["number"])))
    i=issue(int(issues[0]["number"]))
    emit(out,gh_out,{"status":"work","issue":i,"branch":f"{a.branch_prefix}{i['number']}","pr":None}); return 0

if __name__=="__main__": raise SystemExit(main())
