#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
T="$(mktemp -d)"
trap 'rm -rf "$T"' EXIT
cd "$T"
git init -q
git config user.name test
git config user.email test@example.com
mkdir -p .github/workflows src
echo base > src/app.txt
echo safe > .github/workflows/opencode-frontier.yml
git add .
git commit -qm base
base="$(git rev-parse HEAD)"
cat > protected.txt <<'POLICY'
.github/workflows/opencode-*.yml
POLICY
echo candidate >> src/app.txt
python3 "$ROOT/scripts/check-protected.py" --rules protected.txt --base "$base" --head WORKTREE
echo tampered >> .github/workflows/opencode-frontier.yml
if python3 "$ROOT/scripts/check-protected.py" --rules protected.txt --base "$base" --head WORKTREE; then
  echo "protected path modification unexpectedly accepted" >&2
  exit 1
fi
echo "protected path tests passed"
