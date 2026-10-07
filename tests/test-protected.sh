#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
T="$(mktemp -d)"
trap 'rm -rf "$T"' EXIT

cd "$T"
/usr/bin/git init -q
/usr/bin/git config user.name test
/usr/bin/git config user.email test@example.com
mkdir -p .github/workflows src .opencode-actions
printf 'name: old\n' > .github/workflows/opencode-frontier.yml
printf 'ok\n' > src/app.txt
printf '.github/workflows/opencode-frontier.yml\n.opencode-actions/**\n' > .opencode-actions/protected-paths.txt
/usr/bin/git add .
/usr/bin/git commit -qm base
base="$(/usr/bin/git rev-parse HEAD)"

printf 'changed\n' >> src/app.txt
/usr/bin/python3 "$ROOT/scripts/check-protected.py"   --rules .opencode-actions/protected-paths.txt --base "$base" --head WORKTREE

printf 'tampered\n' >> .github/workflows/opencode-frontier.yml
if /usr/bin/python3 "$ROOT/scripts/check-protected.py"   --rules .opencode-actions/protected-paths.txt --base "$base" --head WORKTREE; then
  echo "protected path change unexpectedly accepted" >&2
  exit 1
fi

echo "protected-path tests passed"
