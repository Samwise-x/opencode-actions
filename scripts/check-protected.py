#!/usr/bin/env python3
from __future__ import annotations
import argparse, fnmatch, subprocess, sys
from pathlib import Path

def rules(path: Path) -> list[str]:
    if not path.is_file(): raise SystemExit(f"protected path policy missing: {path}")
    out=[x.strip() for x in path.read_text(encoding="utf-8").splitlines() if x.strip() and not x.strip().startswith("#")]
    if not out: raise SystemExit("protected path policy is empty")
    return out

def changed(base: str, head: str) -> list[str]:
    spec=base if head=="WORKTREE" else f"{base}..{head}"
    p=subprocess.run(["/usr/bin/git","diff","--name-only",spec],check=True,text=True,capture_output=True)
    return [x for x in p.stdout.splitlines() if x]

def main() -> int:
    p=argparse.ArgumentParser(); p.add_argument("--rules",required=True); p.add_argument("--base",required=True); p.add_argument("--head",default="WORKTREE")
    a=p.parse_args(); violations=[]
    for path in changed(a.base,a.head):
        for pattern in rules(Path(a.rules)):
            if fnmatch.fnmatch(path,pattern) or fnmatch.fnmatch("/"+path,pattern):
                violations.append((path,pattern)); break
    if violations:
        print("protected control-plane path modification rejected:",file=sys.stderr)
        for path,pattern in violations: print(f"  {path} (matched {pattern})",file=sys.stderr)
        return 1
    return 0
if __name__=="__main__": raise SystemExit(main())
