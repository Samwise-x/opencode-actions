#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RULESET = "opencode-canonical-admission"

TRIAGE_LABELS = {
    "needs-triage": "Maintainer evaluation required",
    "needs-info": "Waiting on required information",
    "ready-for-agent": "Fully specified and ready for an agent",
    "ready-for-human": "Requires human judgment or authority",
    "wontfix": "Will not be actioned",
}

MANAGED = {
    "templates/frontier.yml": ".github/workflows/opencode-frontier.yml",
    "templates/candidate-validation.yml": ".github/workflows/opencode-candidate-validation.yml",
    "templates/admit.yml": ".github/workflows/opencode-admit.yml",
    "templates/frontier.md": ".github/opencode/frontier.md",
    "templates/harden-runtime.js": ".opencode/plugins/harden-runtime.js",
}

AGENT_DOCS = (
    "docs/agents/issue-tracker.md",
    "docs/agents/triage-labels.md",
    "docs/agents/domain.md",
    "docs/agents/engineering.md",
)

REQUIRED_OPENCODE_EDIT_DENIES = (
    ".git/**",
    ".github/workflows/opencode-*.yml",
    ".github/opencode/**",
    ".opencode-actions/**",
    ".opencode/plugins/**",
    "opencode.json",
    "opencode.jsonc",
    "AGENTS.md",
    "CONTEXT.md",
    "docs/adr/**",
    "docs/agents/**",
    "flake.nix",
    "flake.lock",
    "dagger.json",
    "dagger/**",
)

CONTEXT = """# Domain language

Add only resolved domain vocabulary whose precise meaning affects execution.
"""

FLAKE = """{
  description = "Repository validation environment";
  inputs.nixpkgs.url = "github:NixOS/nixpkgs/2833a4f2f08058f980a143c9fb447953ef15f1cb";

  outputs = { nixpkgs, ... }:
    let systems = [ "x86_64-linux" "aarch64-linux" ];
    in {
      devShells = nixpkgs.lib.genAttrs systems (system:
        let pkgs = import nixpkgs { inherit system; };
        in { default = pkgs.mkShell { packages = [ pkgs.dagger ]; }; });
    };
}
"""

DAGGER_JSON = """{
  "name": "validation",
  "sdk": { "source": "go" },
  "source": "dagger"
}
"""

DAGGER_GO = """package main

type Validation struct{}

// Validate is the minimum greenfield validation seam.
// Replace its implementation as real repository checks appear.
func (m *Validation) Validate() string {
	return "ok"
}
"""


class Error(RuntimeError):
    pass


def cmd(args, cwd, *, input_text=None, check=True):
    p = subprocess.run(
        args, cwd=cwd, input=input_text, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    if check and p.returncode:
        detail = (p.stderr or p.stdout).strip()
        raise Error(f"{args[0]} failed: {detail or p.returncode}")
    return p


def require(name):
    if shutil.which(name) is None:
        raise Error(f"required tool is missing: {name}")


def json_cmd(args, cwd):
    p = cmd(args, cwd)
    try:
        return json.loads(p.stdout or "null")
    except json.JSONDecodeError as exc:
        raise Error(f"{args[0]} returned invalid JSON") from exc


def load_json(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise Error(f"invalid JSON in {path.name}: {exc}") from exc


def ensure_repo(target):
    require("git")
    if cmd(["git", "rev-parse", "--is-inside-work-tree"], target, check=False).returncode:
        raise Error("target must already be a Git repository")
    if cmd(["git", "diff", "--name-only", "--diff-filter=U"], target).stdout.strip():
        raise Error("target has unresolved Git conflicts")


def write_missing(target, relative, content, changed):
    path = target / relative
    if path.exists():
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    changed.append(relative)


def install_exact(target, source_rel, target_rel, changed):
    source = ROOT / source_rel
    destination = target / target_rel
    desired = source.read_bytes()
    if destination.exists():
        if destination.read_bytes() != desired:
            raise Error(f"managed path differs; refusing overwrite: {target_rel}")
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(desired)
    changed.append(target_rel)


def install_protected_paths(target, changed):
    source = ROOT / "templates/protected-paths.txt"
    destination = target / ".opencode-actions/protected-paths.txt"
    required_text = source.read_text(encoding="utf-8")
    if not destination.exists():
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(required_text, encoding="utf-8")
        changed.append(".opencode-actions/protected-paths.txt")
        return

    existing = destination.read_text(encoding="utf-8")
    have = {
        line.strip() for line in existing.splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }
    missing = [
        line.strip() for line in required_text.splitlines()
        if line.strip() and not line.lstrip().startswith("#") and line.strip() not in have
    ]
    if missing:
        destination.write_text(existing.rstrip() + "\n" + "\n".join(missing) + "\n", encoding="utf-8")
        changed.append(".opencode-actions/protected-paths.txt")


def install_opencode(target, changed):
    path = target / "opencode.json"
    jsonc = target / "opencode.jsonc"
    if jsonc.exists():
        raise Error("opencode.jsonc is present; refusing ambiguous OpenCode configuration")

    if not path.exists():
        install_exact(target, "templates/opencode.json", "opencode.json", changed)
        return

    config = load_json(path)
    if config.get("share") != "disabled":
        raise Error("existing opencode.json must set share=disabled")

    edit = (config.get("permission") or {}).get("edit")
    if edit == "deny":
        return
    if not isinstance(edit, dict):
        raise Error("existing opencode.json must deny protected edit paths")

    missing = [pattern for pattern in REQUIRED_OPENCODE_EDIT_DENIES if edit.get(pattern) != "deny"]
    if missing:
        raise Error(
            "existing opencode.json is missing required edit denies: "
            + ", ".join(missing)
        )


def install_local(target):
    changed = []
    for source, destination in MANAGED.items():
        install_exact(target, source, destination, changed)
    install_protected_paths(target, changed)
    install_opencode(target, changed)

    if not (target / "AGENTS.md").exists():
        write_missing(target, "AGENTS.md", (ROOT / "AGENTS.md").read_text(encoding="utf-8"), changed)
    for relative in AGENT_DOCS:
        write_missing(target, relative, (ROOT / relative).read_text(encoding="utf-8"), changed)
    write_missing(target, "CONTEXT.md", CONTEXT, changed)
    write_missing(target, "flake.nix", FLAKE, changed)

    if not any((target / name).exists() for name in ("dagger.json", "dagger.toml", "dagger-module.toml")):
        write_missing(target, "dagger.json", DAGGER_JSON, changed)
        write_missing(target, "dagger/main.go", DAGGER_GO, changed)

    dagger_json = target / "dagger.json"
    if dagger_json.is_file():
        load_json(dagger_json)

    cmd(["git", "diff", "--check"], target)
    return changed


def gh(args, target, *, input_text=None):
    return cmd(["gh", *args], target, input_text=input_text)


def gh_json(args, target):
    return json_cmd(["gh", *args], target)


def get_ruleset(target, slug):
    for item in gh_json(["api", f"repos/{slug}/rulesets"], target) or []:
        if item.get("name") == RULESET and item.get("id") is not None:
            return gh_json(["api", f"repos/{slug}/rulesets/{item['id']}"], target)
    return None


def actor_for(existing):
    raw = os.environ.get("OPENCODE_ADMISSION_BYPASS_ACTOR_ID")
    actor_type = os.environ.get("OPENCODE_ADMISSION_BYPASS_ACTOR_TYPE", "Integration")
    if raw:
        try:
            return int(raw), actor_type
        except ValueError as exc:
            raise Error("OPENCODE_ADMISSION_BYPASS_ACTOR_ID must be an integer") from exc
    bypass = (existing or {}).get("bypass_actors") or []
    if len(bypass) == 1 and bypass[0].get("actor_id") is not None and bypass[0].get("actor_type"):
        return int(bypass[0]["actor_id"]), str(bypass[0]["actor_type"])
    return None


def ruleset_ok(existing, actor):
    if not existing or existing.get("enforcement") != "active":
        return False
    include = set(((existing.get("conditions") or {}).get("ref_name") or {}).get("include") or [])
    if "refs/heads/main" not in include:
        return False
    actor_id, actor_type = actor
    bypass = existing.get("bypass_actors") or []
    if len(bypass) != 1:
        return False
    bypass_ok = (
        int(bypass[0].get("actor_id", -1)) == actor_id
        and bypass[0].get("actor_type") == actor_type
        and bypass[0].get("bypass_mode", "always") == "always"
    )
    rules = {item.get("type"): item for item in existing.get("rules") or []}
    checks = {
        item.get("context")
        for item in (rules.get("required_status_checks", {}).get("parameters") or {}).get("required_status_checks", [])
    }
    return (
        bypass_ok
        and {"deletion", "non_fast_forward", "pull_request", "required_status_checks"} <= set(rules)
        and {"deterministic", "security"} <= checks
    )


def preflight_github(target):
    require("gh")
    gh(["auth", "status"], target)

    repo = gh_json(["repo", "view", "--json", "nameWithOwner,defaultBranchRef"], target)
    slug = repo["nameWithOwner"]
    if (repo.get("defaultBranchRef") or {}).get("name") != "main":
        raise Error("canonical branch must be main")

    secrets = {x["name"] for x in gh_json(["secret", "list", "--json", "name"], target) or []}
    variables = {
        x["name"]: str(x.get("value", ""))
        for x in gh_json(["variable", "list", "--json", "name,value"], target) or []
    }
    existing = get_ruleset(target, slug)
    actor = actor_for(existing)

    missing = [
        name for name in ("OPENCODE_API_KEY", "ADMISSION_TOKEN")
        if name not in secrets and not os.environ.get(name)
    ]
    if "OPENCODE_MODEL" not in variables and not os.environ.get("OPENCODE_MODEL"):
        missing.append("OPENCODE_MODEL")
    if actor is None:
        missing.append("OPENCODE_ADMISSION_BYPASS_ACTOR_ID")
    if missing:
        raise Error("GitHub bootstrap prerequisites missing: " + ", ".join(missing))
    if existing and not ruleset_ok(existing, actor):
        raise Error(f"existing {RULESET} ruleset does not satisfy the playbook contract")

    return slug, secrets, variables, existing, actor


def ruleset_body(actor):
    actor_id, actor_type = actor
    return {
        "name": RULESET,
        "target": "branch",
        "enforcement": "active",
        "bypass_actors": [{"actor_id": actor_id, "actor_type": actor_type, "bypass_mode": "always"}],
        "conditions": {"ref_name": {"include": ["refs/heads/main"], "exclude": []}},
        "rules": [
            {"type": "deletion"},
            {"type": "non_fast_forward"},
            {
                "type": "pull_request",
                "parameters": {
                    "allowed_merge_methods": ["merge", "squash", "rebase"],
                    "dismiss_stale_reviews_on_push": False,
                    "require_code_owner_review": False,
                    "require_last_push_approval": False,
                    "required_approving_review_count": 0,
                    "required_review_thread_resolution": False,
                },
            },
            {
                "type": "required_status_checks",
                "parameters": {
                    "do_not_enforce_on_create": False,
                    "required_status_checks": [
                        {"context": "deterministic"},
                        {"context": "security"},
                    ],
                    "strict_required_status_checks_policy": True,
                },
            },
        ],
    }


def configure_github(target, state):
    slug, secrets, variables, existing, actor = state
    changed = []

    labels = {x["name"] for x in gh_json(["label", "list", "--limit", "1000", "--json", "name"], target) or []}
    for name, description in TRIAGE_LABELS.items():
        if name in labels:
            continue
        gh([
            "label", "create", name,
            "--description", description,
            "--color", "ededed",
        ], target)
        changed.append(f"github:label:{name}")

    for name in ("OPENCODE_MODEL", "OPENCODE_ALLOWED_HOSTS"):
        desired = os.environ.get(name)
        if desired is not None and variables.get(name) != desired:
            gh(["variable", "set", name, "--body", desired], target)
            changed.append(f"github:variable:{name}")

    for name in ("OPENCODE_API_KEY", "ADMISSION_TOKEN"):
        if name not in secrets:
            gh(["secret", "set", name], target, input_text=os.environ[name])
            changed.append(f"github:secret:{name}")

    if existing is None:
        gh(
            ["api", "--method", "POST", f"repos/{slug}/rulesets", "--input", "-"],
            target,
            input_text=json.dumps(ruleset_body(actor)),
        )
        changed.append(f"github:ruleset:{RULESET}")

    return changed


def validate_external(target):
    require("nix")
    changed = []
    if not (target / "flake.lock").exists():
        cmd(["nix", "flake", "lock"], target)
        if not (target / "flake.lock").exists():
            raise Error("nix flake lock did not create flake.lock")
        changed.append("flake.lock")
    cmd(["nix", "develop", "--no-write-lock-file", "--command", "dagger", "call", "validate"], target)
    return changed


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", default=".")
    target = Path(parser.parse_args().target).expanduser().resolve()
    if not target.is_dir():
        raise Error(f"target directory does not exist: {target}")

    ensure_repo(target)
    github_state = preflight_github(target)
    changed = install_local(target)
    changed.extend(validate_external(target))
    changed.extend(configure_github(target, github_state))

    if changed:
        print("bootstrap: changed")
        for item in changed:
            print(f"  {item}")
    else:
        print("bootstrap: converged (no changes)")


if __name__ == "__main__":
    try:
        main()
    except Error as exc:
        print(f"bootstrap: {exc}", file=sys.stderr)
        raise SystemExit(2)
