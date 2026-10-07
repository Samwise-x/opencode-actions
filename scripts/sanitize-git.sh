#!/usr/bin/env bash
set -euo pipefail
: "${GITHUB_REPOSITORY:?GITHUB_REPOSITORY required}"
server="${GITHUB_SERVER_URL:-https://github.com}"
safe_hooks="${RUNNER_TEMP:-/tmp}/opencode-empty-hooks"
mkdir -p "$safe_hooks"
for key in core.hooksPath credential.helper http.proxy https.proxy http.https://github.com/.extraheader; do
  /usr/bin/git config --local --unset-all "$key" 2>/dev/null || true
done
/usr/bin/git config --local core.hooksPath "$safe_hooks"
/usr/bin/git remote set-url origin "${server}/${GITHUB_REPOSITORY}.git"
