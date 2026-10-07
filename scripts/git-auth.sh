#!/usr/bin/env bash
set -euo pipefail
case "${1:-}" in
  enable)
    : "${GH_TOKEN:?GH_TOKEN required}"
    basic="$(printf 'x-access-token:%s' "$GH_TOKEN" | base64 -w0)"
    git config --local http.https://github.com/.extraheader "AUTHORIZATION: basic $basic"
    ;;
  disable)
    git config --local --unset-all http.https://github.com/.extraheader 2>/dev/null || true
    ;;
  *) echo "usage: $0 enable|disable" >&2; exit 2 ;;
esac
