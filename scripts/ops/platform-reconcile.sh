#!/usr/bin/env bash
# Canonical: platform reconcile (default dry-run)
set -euo pipefail
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
# shellcheck disable=SC1091
source "${repo_root}/scripts/dev/lib/common.sh"
load_env "${repo_root}"
cd "${repo_root}/services/control-plane"
exec "${repo_root}/scripts/dev/python.sh" -m app.platform_recovery.reconcile_cli "$@"
