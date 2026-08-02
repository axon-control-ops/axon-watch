#!/usr/bin/env bash
# Gate 6 acceptance test check — focused suite that fits the verifier timeout.
# Full contract coverage stays in run_contract_unit_tests.sh (Fast Gate / CI).
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${repo_root}"

source "${repo_root}/scripts/dev/lib/common.sh"
"${repo_root}/scripts/dev/ensure-python-deps.sh"
python_bin="$(resolve_python "${repo_root}")"

gate6_tests=(
  tests.test_gate6_verifier_contract
  tests.test_gate6_project_contract
  tests.test_gate6_timeout_safe_suite
  tests.test_guardrail_file_sizes
  tests.test_ci_gate_contract
  tests.test_critical_review_clause
  tests.test_gate2_auth_containment
  tests.test_gate3_worker_isolation
  tests.test_gate4_task_ledger
  tests.test_run_state_transitions
  tests.test_safe_improvement_gate
  tests.test_workspace_worker_prompt
  tests.test_failure_detail
)

status=0
echo "contract unit tests: gate6 acceptance suite"
for test_module in "${gate6_tests[@]}"; do
  echo "contract module: ${test_module}"
  "${python_bin}" -m unittest -v "${test_module}" || status=1
done

exit "${status}"
