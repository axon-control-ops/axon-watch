#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${repo_root}"

if [[ -x "${repo_root}/.venv/bin/python3" ]]; then
  python3="${repo_root}/.venv/bin/python3"
else
  python3="python3"
fi

"${python3}" "${repo_root}/scripts/render-howto-handbook-pdf.py" "$@"

echo
echo "How-To Handbook source: docs/HOW-TO-HANDBOOK.md (+ linked docs/how-to/*.md)"
echo "Artifact paths are the renderer results printed above."
