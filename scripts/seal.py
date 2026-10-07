#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, os
from datetime import datetime, timezone
from pathlib import Path

def main()->int:
    p=argparse.ArgumentParser()
    p.add_argument("--frontier-evidence",required=True); p.add_argument("--candidate",required=True)
    p.add_argument("--pr",type=int,required=True); p.add_argument("--required-check",action="append",default=[])
    p.add_argument("--output",required=True); a=p.parse_args()
    path=Path(a.frontier_evidence); raw=path.read_bytes(); evidence=json.loads(raw)
    if evidence.get("schema")!=2 or evidence.get("kind")!="agent-attempt": raise SystemExit("unsupported frontier evidence")
    if evidence.get("status")!="prevalidated": raise SystemExit("frontier evidence is not prevalidated")
    if evidence.get("candidate_sha")!=a.candidate: raise SystemExit("candidate SHA mismatch")
    if int(evidence.get("pr_number",0))!=a.pr: raise SystemExit("PR number mismatch")
    if int(evidence.get("opencode_exit",1))!=0 or int(evidence.get("validation_exit",1))!=0: raise SystemExit("frontier execution failed")
    doc={
      "schema":1,"kind":"qualified-candidate","repository":os.environ["GITHUB_REPOSITORY"],
      "candidate_sha":a.candidate,"base_sha":evidence["base_sha"],"issue_number":int(evidence["issue_number"]),
      "pr_number":a.pr,"attempt_id":evidence["attempt_id"],"model":evidence.get("model"),"agent":evidence.get("agent"),
      "frontier_evidence_sha256":hashlib.sha256(raw).hexdigest(),
      "validation_run_id":os.environ.get("GITHUB_RUN_ID",""),
      "validation_workflow_ref":os.environ.get("GITHUB_WORKFLOW_REF",""),
      "required_checks":a.required_check,
      "generated_at":datetime.now(timezone.utc).isoformat()
    }
    out=Path(a.output); out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(doc,indent=2,sort_keys=True)+"\n",encoding="utf-8"); return 0
if __name__=="__main__": raise SystemExit(main())
