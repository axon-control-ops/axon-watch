#!/usr/bin/env bash
# VERIFY CLEAN BASELINE — isolate test state, do not share .local/state.
set -euo pipefail
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${repo_root}"

evidence_dir="${repo_root}/.local/verify-evidence"
mkdir -p "${evidence_dir}"
stamp="$(date -u +%Y%m%dT%H%M%SZ)"
summary="${evidence_dir}/clean-baseline-${stamp}.txt"
json_out="${evidence_dir}/clean-baseline-${stamp}.json"
state_dir="$(mktemp -d "${TMPDIR:-/tmp}/axon-clean-baseline.XXXXXX")"
export AXON_WATCH_STATE_DIR="${state_dir}"
export AXON_WATCH_CONTROL_PLANE_DB="${state_dir}/control-plane.sqlite3"
export AXON_WATCH_WORKER_SCHEDULER=0

{
  echo "VERIFY CLEAN BASELINE ${stamp}"
  echo "isolated state: ${state_dir}"
  echo
  echo "=== process inventory ==="
  "${repo_root}/scripts/ops/platform-doctor.sh" || true
  echo
  echo "=== recovery + security tests ==="
} | tee "${summary}"

set +e
"${repo_root}/scripts/dev/python.sh" -m unittest \
  tests.test_platform_recovery \
  tests.test_platform_recovery_signals \
  tests.test_sensitive_get_auth \
  tests.test_run_stale_reconcile \
  tests.test_restart_reconcile \
  tests.test_gate2_auth_containment \
  -v
py_status=$?
npm run test -w @axon-watch/console-web -- \
  src/lib/recovery-center-view.test.ts \
  src/lib/mockup-shell-view.test.ts \
  src/lib/live-events-session.test.ts
js_status=$?
set -e

{
  echo
  echo "python_status=${py_status}"
  echo "javascript_status=${js_status}"
  if [[ "${py_status}" -eq 0 && "${js_status}" -eq 0 ]]; then
    echo "CLEAN BASELINE PASS"
  else
    echo "CLEAN BASELINE FAIL"
  fi
} | tee -a "${summary}"

python3 - <<PY
import json
from pathlib import Path
payload = {
  "stamp": "${stamp}",
  "python_status": ${py_status},
  "javascript_status": ${js_status},
  "state_dir": "${state_dir}",
  "summary": "${summary}",
  "status": "PASS" if ${py_status} == 0 and ${js_status} == 0 else "FAIL",
}
Path("${json_out}").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
print(json.dumps(payload, indent=2))
PY

rm -rf "${state_dir}"
if [[ "${py_status}" -ne 0 || "${js_status}" -ne 0 ]]; then
  exit 1
fi
