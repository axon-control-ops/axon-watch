#!/usr/bin/env bash
# Auto change → critical review → CI verify loop (operator / Night Watch helper).
# Usage:
#   ./scripts/ops/change-verify-loop.sh
#   ./scripts/ops/change-verify-loop.sh --watch   # re-run when git dirty state changes
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${repo_root}"

watch_mode=0
if [[ "${1:-}" == "--watch" ]]; then
  watch_mode=1
fi

critical_review_clause='Critically review all your previous work for factual errors, missing steps, unsupported assumptions, and any invented or unverified details. Then rewrite the answer to correct those issues and make it more precise and reliable. End with Confidence: X/10.'

fingerprint() {
  git status --porcelain
  git rev-parse HEAD 2>/dev/null || true
}

run_once() {
  echo "=== change-verify-loop $(date -Is) ==="
  echo "CRITICAL REVIEW CLAUSE (required before claiming green):"
  echo "  ${critical_review_clause}"
  echo
  echo "Working tree:"
  git status -sb
  echo

  if [[ -n "$(git status --porcelain)" ]]; then
    echo "Dirty tree detected — run critical review on the diff before merge claims."
    git diff --stat || true
  else
    echo "Working tree clean relative to HEAD."
  fi
  echo

  echo "Running verify:contracts ..."
  if npm run verify:contracts; then
    echo
    echo "VERIFY: contracts PASSED"
    echo "Confidence note: still require human/agent critical review of claims before merge."
    return 0
  fi

  echo
  echo "VERIFY: contracts FAILED"
  echo "Do not report bare FAILED — capture the exact failing check, file, and error above."
  return 1
}

if [[ "${watch_mode}" -eq 0 ]]; then
  run_once
  exit $?
fi

echo "Watching for git changes (Ctrl+C to stop)..."
prev=""
while true; do
  cur="$(fingerprint)"
  if [[ "${cur}" != "${prev}" ]]; then
    prev="${cur}"
    run_once || true
  fi
  sleep 20
done
