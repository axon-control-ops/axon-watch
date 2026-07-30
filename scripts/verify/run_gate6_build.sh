#!/usr/bin/env bash
# Gate 6 build — skip console-web build in disposable worker isolations.
set -euo pipefail
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${repo_root}"
if [[ -f "${repo_root}/.axon-si/baseline.json" ]]; then
  echo "gate6 build: skipped in worker isolation (.axon-si); Fast Gate covers apps/"
  exit 0
fi
npm run build --workspace=apps/console-web
