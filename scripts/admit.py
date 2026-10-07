#!/usr/bin/env python3
from __future__ import annotations
import argparse, base64, fnmatch, json, os, subprocess, sys, tempfile, urllib.error, urllib.request
from pathlib import Path
from typing import Any

API=os.environ.get("GITHUB_API_URL","https://api.github.com")

def request(method:str,path:str,token:str,body:dict[str,Any]|None=None)->Any:
    data=None if body is None else json.dumps(body).encode()
    req=urllib.request.Request(f"{API}{path}",data=data,method=method,headers={
      "Accept":"application/vnd.github+json","Authorization":f"Bearer {token}",
      "X-GitHub-Api-Version":"2022-11-28","User-Agent":"Samwise-x/opencode-actions",
      **({"Content-Type":"application/json"} if data is not None else {})})
    try:
        with urllib.request.urlopen(req,timeout=30) as r:
            payload=r.read(); return json.loads(payload) if payload else {}
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"GitHub API {method} {path} failed: {exc.code} {exc.read().decode(errors='replace')}") from exc

def run_git(args:list[str],env:dict[str,str])->str:
    p=subprocess.run(["/usr/bin/git",*args],check=True,text=True,capture_output=True,env=env)
    return p.stdout.strip()

def load_rules(path:Path)->list[str]:
    if not path.is_file(): raise SystemExit(f"protected paths file missing: {path}")
    return [x.strip() for x in path.read_text().splitlines() if x.strip() and not x.strip().startswith("#")]

def main()->int:
    p=argparse.ArgumentParser(); p.add_argument("--repository",default=os.environ.get("GITHUB_REPOSITORY",""))
    p.add_argument("--pr",type=int,required=True); p.add_argument("--candidate-sha",required=True)
    p.add_argument("--qualification",required=True); p.add_argument("--protected-paths",required=True)
    p.add_argument("--required-check",action="append",default=[]); a=p.parse_args()
    token=os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if not token: raise SystemExit("GitHub token required")
    q=json.loads(Path(a.qualification).read_text())
    if q.get("schema")!=1 or q.get("kind")!="qualified-candidate": raise SystemExit("unsupported qualification")
    if q.get("repository")!=a.repository or q.get("candidate_sha")!=a.candidate_sha or int(q.get("pr_number",0))!=a.pr:
        raise SystemExit("qualification identity mismatch")
    base_sha=q["base_sha"]; issue=int(q["issue_number"]); owner,repo=a.repository.split("/",1)
    pr=request("GET",f"/repos/{owner}/{repo}/pulls/{a.pr}",token)
    if pr.get("state")!="open": raise SystemExit("PR is not open")
    if pr.get("head",{}).get("sha")!=a.candidate_sha: raise SystemExit("PR head moved")
    base_ref=pr.get("base",{}).get("ref")
    current=request("GET",f"/repos/{owner}/{repo}/git/ref/heads/{base_ref}",token).get("object",{}).get("sha")
    if current!=base_sha: raise SystemExit(f"canonical base moved: evidence={base_sha} current={current}")

    checks=request("GET",f"/repos/{owner}/{repo}/commits/{a.candidate_sha}/check-runs?per_page=100",token)
    by_name={}
    for check in checks.get("check_runs",[]): by_name.setdefault(check.get("name",""),[]).append(check)
    required=a.required_check or q.get("required_checks",[])
    for name in required:
        rows=by_name.get(name,[])
        if not rows: raise SystemExit(f"required check missing: {name}")
        latest=max(rows,key=lambda x:int(x.get("id",0)))
        if latest.get("status")!="completed" or latest.get("conclusion")!="success":
            raise SystemExit(f"required check not successful: {name}")

    env={"PATH":"/usr/bin:/bin","HOME":tempfile.mkdtemp(prefix="opencode-admit-"),"GIT_CONFIG_GLOBAL":"/dev/null",
         "GIT_CONFIG_SYSTEM":"/dev/null","GITHUB_REPOSITORY":a.repository}
    auth=base64.b64encode(f"x-access-token:{token}".encode()).decode()
    common=["-c","core.hooksPath=/dev/null","-c","http.proxy=","-c","https.proxy=",
            "-c",f"http.https://github.com/.extraheader=AUTHORIZATION: basic {auth}"]
    remote=f"https://github.com/{a.repository}.git"
    run_git([*common,"remote","set-url","origin",remote],env)
    run_git([*common,"fetch","--no-tags","origin",base_ref,pr["head"]["ref"]],env)
    local_base=run_git(["rev-parse",f"origin/{base_ref}"],env); local_head=run_git(["rev-parse",f"origin/{pr['head']['ref']}"],env)
    if local_base!=base_sha or local_head!=a.candidate_sha: raise SystemExit("fetched refs do not match qualification")
    subprocess.run(["/usr/bin/git","merge-base","--is-ancestor",base_sha,a.candidate_sha],check=True,env=env)

    changed=run_git(["diff","--name-only",f"{base_sha}..{a.candidate_sha}"],env).splitlines()
    violations=[]
    for path in changed:
        for pattern in load_rules(Path(a.protected_paths)):
            if fnmatch.fnmatch(path,pattern) or fnmatch.fnmatch("/"+path,pattern): violations.append((path,pattern)); break
    if violations: raise SystemExit("protected path changed: "+", ".join(x[0] for x in violations))

    run_git([*common,"push","origin",f"--force-with-lease=refs/heads/{base_ref}:{base_sha}",
             f"{a.candidate_sha}:refs/heads/{base_ref}"],env)
    landed=request("GET",f"/repos/{owner}/{repo}/git/ref/heads/{base_ref}",token).get("object",{}).get("sha")
    if landed!=a.candidate_sha: raise SystemExit("canonical ref did not land on exact candidate")
    request("PATCH",f"/repos/{owner}/{repo}/issues/{issue}",token,{"state":"closed","state_reason":"completed"})
    print(json.dumps({"admitted":True,"candidate_sha":a.candidate_sha,"base_ref":base_ref,"issue":issue,"pr":a.pr},sort_keys=True)); return 0

if __name__=="__main__":
    try: raise SystemExit(main())
    except RuntimeError as exc:
        print(str(exc),file=sys.stderr); raise SystemExit(1)
