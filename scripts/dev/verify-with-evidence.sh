#!/usr/bin/env bash
# Run full verify using locally collected latency evidence when available.

set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${repo_root}"

evidence_dir="${repo_root}/.local/verify"
shell_report="${evidence_dir}/shell-boot-report.json"
runtime_samples="${evidence_dir}/runtime-summary-latency.json"
watch_samples="${evidence_dir}/watch-summary-latency.json"

verify_args=()

if [[ -f "${shell_report}" ]]; then
  verify_args+=(--shell-boot-report "${shell_report}")
fi
if [[ -f "${runtime_samples}" ]]; then
  verify_args+=(--runtime-latency-samples "${runtime_samples}")
fi
if [[ -f "${watch_samples}" ]]; then
  verify_args+=(--watch-latency-samples "${watch_samples}")
fi

npm run verify -- "${verify_args[@]}"
