#!/usr/bin/env bash
# Gate 6 typecheck — skip vue-tsc in disposable worker isolations (OOM-prone).
set -euo pipefail
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${repo_root}"
if [[ -f "${repo_root}/.axon-si/baseline.json" ]]; then
  echo "gate6 typecheck: skipped in worker isolation (.axon-si); Fast Gate covers apps/"
  exit 0
fi
npm run typecheck --workspace=apps/console-web
