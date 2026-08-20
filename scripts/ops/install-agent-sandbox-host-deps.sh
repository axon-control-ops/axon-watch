#!/usr/bin/env bash
# Install host packages required for sandboxed Cursor agent dispatch.
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
source "${repo_root}/scripts/dev/lib/common.sh"

missing=()
for cmd in bwrap rg git node npm; do
  if ! command -v "${cmd}" >/dev/null 2>&1; then
    missing+=("${cmd}")
  fi
done

if ((${#missing[@]} == 0)); then
  echo "Agent sandbox host prerequisites already present: bwrap rg git node npm"
  exit 0
fi

if ! command -v apt-get >/dev/null 2>&1; then
  echo "Missing sandbox host tools: ${missing[*]}" >&2
  echo "Install bubblewrap, ripgrep, git, node, and npm using your system package manager." >&2
  exit 1
fi

packages=()
for cmd in "${missing[@]}"; do
  case "${cmd}" in
    bwrap) packages+=(bubblewrap) ;;
    rg) packages+=(ripgrep) ;;
    git) packages+=(git) ;;
    node) packages+=(nodejs) ;;
    npm) packages+=(npm) ;;
  esac
done

echo "Installing sandbox host packages: ${packages[*]}"
sudo apt-get update
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y "${packages[@]}"

echo "Installing Axon bin wrappers (axon-agent-terminal-job, axon-assign, …)"
"${repo_root}/scripts/ops/install-bin-wrappers.sh"

echo "Done. Re-run scripts/dev/check-health.sh to verify agent dispatch prerequisites."
