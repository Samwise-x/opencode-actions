#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import os
import stat
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUIRED_DENIES = (
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
    "flake.nix",
    "flake.lock",
    "dagger.json",
    "dagger/**",
)

FAKE_GH = r"""#!/usr/bin/env bash
set -euo pipefail
state="${FAKE_GH_STATE:?}"
mkdir -p "$state/labels" "$state/variables" "$state/secrets"

if [[ "${1:-} ${2:-}" == "auth status" ]]; then
  exit 0
fi

if [[ "${1:-} ${2:-}" == "repo view" ]]; then
  printf '%s\n' '{"nameWithOwner":"example/target","defaultBranchRef":{"name":"main"}}'
  exit 0
fi

if [[ "${1:-} ${2:-}" == "secret list" ]]; then
  find "$state/secrets" -mindepth 1 -maxdepth 1 -type f -printf '%f\n' |
    sort | jq -Rn '[inputs | select(length > 0) | {name:.}]'
  exit 0
fi

if [[ "${1:-} ${2:-}" == "variable list" ]]; then
  first=true
  printf '['
  for file in "$state"/variables/*; do
    [[ -e "$file" ]] || continue
    $first || printf ','
    first=false
    jq -cn --arg name "$(basename "$file")" --rawfile value "$file" \
      '{name:$name,value:($value | rtrimstr("\n"))}'
  done
  printf ']\n'
  exit 0
fi

if [[ "${1:-} ${2:-}" == "label list" ]]; then
  find "$state/labels" -mindepth 1 -maxdepth 1 -type f -printf '%f\n' |
    sort | jq -Rn '[inputs | select(length > 0) | {name:.}]'
  exit 0
fi

if [[ "${1:-} ${2:-}" == "label create" ]]; then
  : > "$state/labels/$3"
  exit 0
fi

if [[ "${1:-} ${2:-}" == "variable set" ]]; then
  name="$3"
  shift 3
  while (($#)); do
    if [[ "$1" == "--body" ]]; then
      printf '%s' "$2" > "$state/variables/$name"
      exit 0
    fi
    shift
  done
  exit 99
fi

if [[ "${1:-} ${2:-}" == "secret set" ]]; then
  cat > "$state/secrets/$3"
  exit 0
fi

if [[ "${1:-}" == "api" ]]; then
  endpoint=""
  method="GET"
  while (($#)); do
    case "$1" in
      --method)
        method="$2"
        shift 2
        ;;
      repos/*)
        endpoint="$1"
        shift
        ;;
      *)
        shift
        ;;
    esac
  done

  if [[ "$method" == "POST" && "$endpoint" == "repos/example/target/rulesets" ]]; then
    jq '. + {id:1}' > "$state/ruleset.json"
    cat "$state/ruleset.json"
    exit 0
  fi

  if [[ "$endpoint" == "repos/example/target/rulesets" ]]; then
    if [[ -f "$state/ruleset.json" ]]; then
      jq '[{id:.id,name:.name}]' "$state/ruleset.json"
    else
      printf '[]\n'
    fi
    exit 0
  fi

  if [[ "$endpoint" == "repos/example/target/rulesets/1" && -f "$state/ruleset.json" ]]; then
    cat "$state/ruleset.json"
    exit 0
  fi
fi

printf 'unsupported fake gh call: %q ' "$@" >&2
printf '\n' >&2
exit 99
"""

FAKE_NIX = r"""#!/usr/bin/env bash
set -euo pipefail
if [[ "${1:-} ${2:-}" == "flake lock" ]]; then
  printf '%s\n' '{"version":1}' > flake.lock
  exit 0
fi
if [[ "${1:-}" == "develop" && "${*: -3}" == "dagger call validate" ]]; then
  exit 0
fi
printf 'unsupported fake nix call: %q ' "$@" >&2
printf '\n' >&2
exit 99
"""


def executable(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR)


def env_for(fake_bin: Path, state: Path) -> dict[str, str]:
    return {
        **os.environ,
        "PATH": f"{fake_bin}{os.pathsep}{os.environ['PATH']}",
        "FAKE_GH_STATE": str(state),
        "OPENCODE_API_KEY": "provider-test",
        "ADMISSION_TOKEN": "admission-test",
        "OPENCODE_MODEL": "opencode/test-model",
        "OPENCODE_ADMISSION_BYPASS_ACTOR_ID": "1234",
    }


def run_make(
    target: Path,
    env: dict[str, str],
    *,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["make", "-f", str(ROOT / "Makefile"), f"TARGET={target}"],
        cwd=ROOT,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=20,
        check=check,
    )


def init_repo(path: Path) -> None:
    subprocess.run(["git", "init", "-q", "-b", "main", str(path)], check=True)
    subprocess.run(["git", "-C", str(path), "config", "user.name", "test"], check=True)
    subprocess.run(
        ["git", "-C", str(path), "config", "user.email", "test@example.com"],
        check=True,
    )


def snapshot(path: Path) -> dict[str, str]:
    return {
        str(file.relative_to(path)): hashlib.sha256(file.read_bytes()).hexdigest()
        for file in sorted(
            file
            for file in path.rglob("*")
            if file.is_file() and ".git" not in file.parts
        )
    }


with tempfile.TemporaryDirectory() as td:
    base = Path(td)
    fake_bin = base / "bin"
    fake_bin.mkdir()
    executable(fake_bin / "gh", FAKE_GH)
    executable(fake_bin / "nix", FAKE_NIX)

    green = base / "green"
    green.mkdir()
    init_repo(green)
    green_state = base / "green-gh"
    green_env = env_for(fake_bin, green_state)

    first_run = run_make(green, green_env)
    assert "bootstrap: changed" in first_run.stdout
    first_files = snapshot(green)
    first_github = snapshot(green_state)

    second_run = run_make(green, green_env)
    assert "bootstrap: converged (no changes)" in second_run.stdout
    assert snapshot(green) == first_files
    assert snapshot(green_state) == first_github

    required = {
        ".github/workflows/opencode-frontier.yml",
        ".github/workflows/opencode-candidate-validation.yml",
        ".github/workflows/opencode-admit.yml",
        ".github/opencode/frontier.md",
        ".opencode-actions/protected-paths.txt",
        ".opencode/plugins/harden-runtime.js",
        "AGENTS.md",
        "CONTEXT.md",
        "flake.nix",
        "flake.lock",
        "dagger.json",
        "dagger/main.go",
        "opencode.json",
    }
    assert required <= set(first_files)
    assert ".github/opencode/**" in (
        green / ".opencode-actions/protected-paths.txt"
    ).read_text()

    ruleset = json.loads((green_state / "ruleset.json").read_text())
    assert ruleset["bypass_actors"] == [{
        "actor_id": 1234,
        "actor_type": "Integration",
        "bypass_mode": "always",
    }]

    brown = base / "brown"
    brown.mkdir()
    init_repo(brown)
    brown_state = base / "brown-gh"
    brown_env = env_for(fake_bin, brown_state)

    custom_opencode = {
        "share": "disabled",
        "model": "example/custom",
        "permission": {
            "edit": {pattern: "deny" for pattern in REQUIRED_DENIES},
        },
    }
    originals = {
        "AGENTS.md": "# custom agents\n",
        "CONTEXT.md": "# Domain language\n\n**widget**: existing term.\n",
        "flake.nix": "{ outputs = _: {}; }\n",
        "flake.lock": "{}\n",
        "dagger.json": '{"name":"existing","sdk":{"source":"go"}}\n',
        "dagger/main.go": "package main\n\ntype Existing struct{}\n",
        "opencode.json": json.dumps(custom_opencode, indent=2) + "\n",
    }
    for name, content in originals.items():
        path = brown / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    run_make(brown, brown_env)
    for name, content in originals.items():
        assert (brown / name).read_text(encoding="utf-8") == content
    first_files = snapshot(brown)
    first_github = snapshot(brown_state)

    second_run = run_make(brown, brown_env)
    assert "bootstrap: converged (no changes)" in second_run.stdout
    assert snapshot(brown) == first_files
    assert snapshot(brown_state) == first_github

    conflict = base / "conflict"
    conflict.mkdir()
    init_repo(conflict)
    conflict_state = base / "conflict-gh"
    conflict_env = env_for(fake_bin, conflict_state)
    path = conflict / ".github/workflows/opencode-frontier.yml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("name: custom\n", encoding="utf-8")
    result = run_make(conflict, conflict_env, check=False)
    assert result.returncode != 0
    assert path.read_text(encoding="utf-8") == "name: custom\n"

    invalid = base / "invalid-opencode"
    invalid.mkdir()
    init_repo(invalid)
    invalid_state = base / "invalid-gh"
    invalid_env = env_for(fake_bin, invalid_state)
    invalid_config = invalid / "opencode.json"
    invalid_config.write_text(
        '{"share":"manual","permission":{"edit":"allow"}}\n',
        encoding="utf-8",
    )
    result = run_make(invalid, invalid_env, check=False)
    assert result.returncode != 0
    assert invalid_config.read_text() == (
        '{"share":"manual","permission":{"edit":"allow"}}\n'
    )

print("bootstrap convergence tests passed")
