#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
if [[ "${AXON_WATCH_SKIP_PYTHON_BOOTSTRAP:-0}" != "1" ]]; then
  "${repo_root}/scripts/dev/ensure-python-deps.sh" >/dev/null
fi
source "${repo_root}/scripts/dev/lib/common.sh"

python_bin="$(resolve_python "${repo_root}")"
exec "${python_bin}" "$@"
