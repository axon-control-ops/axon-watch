#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
source "${repo_root}/scripts/dev/lib/common.sh"
cd "${repo_root}"

python_bin="$(resolve_python)"

if [[ ! -x "${repo_root}/.venv/bin/python3" ]]; then
  echo "Creating Axon-Watch Python venv at ${repo_root}/.venv"
  python3 -m venv "${repo_root}/.venv"
  python_bin="${repo_root}/.venv/bin/python3"
fi

"${python_bin}" -m pip install -q -U pip wheel
"${python_bin}" -m pip install -q -r "${repo_root}/requirements.txt"
