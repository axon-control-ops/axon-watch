#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${repo_root}"

if [[ -x "${repo_root}/.venv/bin/python3" ]]; then
  python3="${repo_root}/.venv/bin/python3"
else
  python3="python3"
fi

"${python3}" "${repo_root}/scripts/docs/build-starter-guide-pdf.py"

echo
echo "Starter guide artifacts:"
echo "  Markdown: docs/AXON-X-STARTER-GUIDE.md"
echo "  HTML:     docs/AXON-X-STARTER-GUIDE.html"
echo "  PDF:      docs/AXON-X-STARTER-GUIDE.pdf"
