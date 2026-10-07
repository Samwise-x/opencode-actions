#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, os, urllib.error, urllib.parse, urllib.request
from typing import Any

API=os.environ.get("GITHUB_API_URL","https://api.github.com")

def api(method:str,path:str,token:str,body:dict[str,Any]|None=None)->Any:
    data=None if body is None else json.dumps(body).encode()
    req=urllib.request.Request(f"{API}{path}",data=data,method=method,headers={
        "Accept":"application/vnd.github+json","Authorization":f"Bearer {token}",
        "X-GitHub-Api-Version":"2022-11-28","User-Agent":"Samwise-x/opencode-actions",
        **({"Content-Type":"application/json"} if data is not None else {})})
    try:
        with urllib.request.urlopen(req,timeout=30) as r:
            payload=r.read(); return json.loads(payload) if payload else {}
    except urllib.error.HTTPError as exc:
        raise SystemExit(f"GitHub API {method} {path} failed: {exc.code} {exc.read().decode(errors='replace')}") from exc

def main()->int:
    p=argparse.ArgumentParser(); p.add_argument("--repository",default=os.environ.get("GITHUB_REPOSITORY",""))
    p.add_argument("--head",required=True); p.add_argument("--base",required=True); p.add_argument("--issue",type=int,required=True)
    p.add_argument("--title",required=True); p.add_argument("--attempt",required=True); p.add_argument("--base-sha",required=True)
    p.add_argument("--candidate-sha",required=True); p.add_argument("--output"); a=p.parse_args()
    token=os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if not token: raise SystemExit("GitHub token required")
    owner,repo=a.repository.split("/",1)
    body=(f"Automated candidate for #{a.issue}.\n\nCloses #{a.issue}\n\n"
          f"Attempt: `{a.attempt}`\nBase: `{a.base_sha}`\nCandidate: `{a.candidate_sha}`\n")
    query=urllib.parse.urlencode({"state":"open","head":f"{owner}:{a.head}","base":a.base})
    existing=api("GET",f"/repos/{owner}/{repo}/pulls?{query}",token)
    if existing:
        pr=api("PATCH",f"/repos/{owner}/{repo}/pulls/{existing[0]['number']}",token,
               {"title":a.title,"body":body,"maintainer_can_modify":False})
    else:
        pr=api("POST",f"/repos/{owner}/{repo}/pulls",token,
               {"title":a.title,"head":a.head,"base":a.base,"body":body,"maintainer_can_modify":False})
    values={"pr_number":pr["number"],"pr_url":pr["html_url"],"pr_head_sha":pr["head"]["sha"]}
    if values["pr_head_sha"]!=a.candidate_sha: raise SystemExit("PR head does not equal candidate SHA")
    if a.output:
        with open(a.output,"a",encoding="utf-8") as f:
            for k,v in values.items(): f.write(f"{k}={v}\n")
    print(json.dumps(values,sort_keys=True)); return 0
if __name__=="__main__": raise SystemExit(main())
