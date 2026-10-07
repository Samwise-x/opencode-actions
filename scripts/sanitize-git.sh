#!/usr/bin/env bash
set -euo pipefail
: "${GITHUB_REPOSITORY:?GITHUB_REPOSITORY required}"
server="${GITHUB_SERVER_URL:-https://github.com}"
[[ -d .git ]] || { echo "expected a normal Git checkout with .git directory" >&2; exit 73; }

# Model execution may write local Git configuration through arbitrary shell code.
# Privileged phases therefore do not try to clean individual keys. They replace
# the local config with a minimal known-good transport configuration.
cat > .git/config <<EOF
[core]
    repositoryformatversion = 0
    filemode = true
    bare = false
    logallrefupdates = true
    hooksPath = /dev/null
[remote "origin"]
    url = ${server}/${GITHUB_REPOSITORY}.git
    fetch = +refs/heads/*:refs/remotes/origin/*
EOF
