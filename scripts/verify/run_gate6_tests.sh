#!/usr/bin/env bash
# Gate 6 tests — full contract suite on bound roots; focused suite in isolations.
set -euo pipefail
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${repo_root}"

if [[ ! -f "${repo_root}/.axon-si/baseline.json" ]]; then
  exec "${repo_root}/scripts/verify/run_contract_unit_tests.sh"
fi

source "${repo_root}/scripts/dev/lib/common.sh"
"${repo_root}/scripts/dev/ensure-python-deps.sh"
python_bin="$(resolve_python "${repo_root}")"

modules=(
  tests.test_gate6_verifier_contract
  tests.test_gate6_project_contract
)

# Include changed Python test modules from the isolation worktree.
while IFS= read -r path; do
  [[ -z "${path}" ]] && continue
  [[ "${path}" == .axon-si || "${path}" == .axon-si/* ]] && continue
  base="$(basename "${path}")"
  if [[ "${base}" == test_*.py && "${path}" == tests/* ]]; then
    mod="tests.${base%.py}"
    # shellcheck disable=SC2076
    if [[ ! " ${modules[*]} " =~ " ${mod} " ]]; then
      modules+=("${mod}")
    fi
  fi
done < <(
  git -C "${repo_root}" status --porcelain -uall \
    | awk '{path=$2; if (path != "" && path != ".axon-si" && path !~ /^\.axon-si\//) print path}'
)

echo "gate6 tests (worker isolation): ${modules[*]}"
status=0
for mod in "${modules[@]}"; do
  echo "contract module: ${mod}"
  if ! "${python_bin}" -m unittest -v "${mod}"; then
    status=1
  fi
done
exit "${status}"
