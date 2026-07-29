#!/usr/bin/env bash
set -euo pipefail

# Full bounce for always-on + bootstrap: stop systemd units if present, then up --force.
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

echo "=== Axon-X restart ==="
"${repo_root}/scripts/dev/down.sh" --systemd "$@"
"${repo_root}/scripts/dev/up.sh" --force "$@"
"${repo_root}/scripts/dev/check-health.sh"
