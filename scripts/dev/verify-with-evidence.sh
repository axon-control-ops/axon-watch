#!/usr/bin/env bash
# Run contracts + console + verification scaffold, preferring local evidence samples.
# Usage: ./scripts/dev/verify-with-evidence.sh [--strict-pending] [--require-live-evidence]

set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${repo_root}"

strict_pending=0
require_live_evidence=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --strict-pending)
      strict_pending=1
      shift
      ;;
    --require-live-evidence)
      require_live_evidence=1
      shift
      ;;
    *)
      echo "unknown argument: $1" >&2
      echo "usage: $0 [--strict-pending] [--require-live-evidence]" >&2
      exit 2
      ;;
  esac
done

evidence_dir="${repo_root}/.local/verify"
shell_report="${evidence_dir}/shell-boot-report.json"
runtime_samples="${evidence_dir}/runtime-summary-latency.json"
watch_samples="${evidence_dir}/watch-summary-latency.json"

if [[ "${require_live_evidence}" -eq 1 ]]; then
  for evidence_path in "${shell_report}" "${runtime_samples}" "${watch_samples}"; do
    if [[ ! -s "${evidence_path}" ]]; then
      echo "required live evidence missing or empty: ${evidence_path}" >&2
      exit 1
    fi
  done
fi

npm run verify:contracts
npm run verify:console-web

scaffold_args=(
  --runtime-payload "${repo_root}/packages/shared-types/fixtures/runtime-summary.example.json"
  --watch-payload "${repo_root}/packages/shared-types/fixtures/watch-summary.example.json"
  --shell-boot-report "${repo_root}/scripts/verify/fixtures/shell-boot-report.dev.json"
  --runtime-latency-samples "${repo_root}/scripts/verify/fixtures/runtime-summary-latency.ci.json"
  --watch-latency-samples "${repo_root}/scripts/verify/fixtures/watch-summary-latency.ci.json"
)

if [[ -f "${shell_report}" ]]; then
  scaffold_args+=(--shell-boot-report "${shell_report}")
fi
if [[ -f "${runtime_samples}" ]]; then
  scaffold_args+=(--runtime-latency-samples "${runtime_samples}")
fi
if [[ -f "${watch_samples}" ]]; then
  scaffold_args+=(--watch-latency-samples "${watch_samples}")
fi
if [[ "${strict_pending}" -eq 1 ]]; then
  scaffold_args+=(--strict-pending)
fi

./scripts/dev/python.sh scripts/verify/all.py "${scaffold_args[@]}"
