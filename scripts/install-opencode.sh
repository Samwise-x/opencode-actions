#!/usr/bin/env bash
set -euo pipefail
VERSION="${1:?version required}"
X64_EXPECTED="${2:?x64 sha256 required}"
ARM64_EXPECTED="${3:?arm64 sha256 required}"

case "$(uname -m)" in
  x86_64|amd64)
    ASSET="opencode-linux-x64.tar.gz"
    EXPECTED="$X64_EXPECTED"
    ;;
  aarch64|arm64)
    ASSET="opencode-linux-arm64.tar.gz"
    EXPECTED="$ARM64_EXPECTED"
    ;;
  *)
    echo "unsupported architecture: $(uname -m)" >&2
    exit 2
    ;;
esac

URL="https://github.com/anomalyco/opencode/releases/download/v${VERSION}/${ASSET}"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

curl --proto '=https' --tlsv1.2 -fsSL --retry 5 --retry-all-errors "$URL" -o "$TMP/opencode.tgz"
printf '%s  %s\n' "$EXPECTED" "$TMP/opencode.tgz" | sha256sum -c --strict -
tar -xzf "$TMP/opencode.tgz" -C "$TMP"
BIN="$(find "$TMP" -type f -name opencode -perm -u+x | head -1)"
[[ -n "$BIN" ]] || { echo "opencode binary not found" >&2; exit 3; }

mkdir -p "$HOME/.local/bin"
install -m 0755 "$BIN" "$HOME/.local/bin/opencode"
printf '%s\n' "$HOME/.local/bin" >> "$GITHUB_PATH"
"$HOME/.local/bin/opencode" --version
