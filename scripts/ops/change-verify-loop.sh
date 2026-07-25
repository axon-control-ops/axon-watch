#!/usr/bin/env bash
# Auto change → critical review → CI verify loop (operator / Night Watch helper).
# Usage:
#   ./scripts/ops/change-verify-loop.sh              # one shot on current tree
#   ./scripts/ops/change-verify-loop.sh --watch      # re-run when git dirty state changes
#   ./scripts/ops/change-verify-loop.sh --head-only  # stash dirty, verify HEAD commit, restore
#
# Note: GitHub Fast Gate green on a PR commit ≠ local dirty tree green.
# This script verifies the tree you have checked out right now (unless --head-only).
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${repo_root}"

watch_mode=0
head_only=0
for arg in "$@"; do
  case "${arg}" in
    --watch) watch_mode=1 ;;
    --head-only) head_only=1 ;;
  esac
done

log_dir="${repo_root}/.axon"
mkdir -p "${log_dir}"
log_file="${log_dir}/change-verify-loop.log"
lock_file="${log_dir}/change-verify-loop.lock"

critical_review_clause='Critically review all your previous work for factual errors, missing steps, unsupported assumptions, and any invented or unverified details. Then rewrite the answer to correct those issues and make it more precise and reliable. End with Confidence: X/10.'

fingerprint() {
  git status --porcelain
  git rev-parse HEAD 2>/dev/null || true
}

other_verify_running() {
  # Exclude this shell's descendants by matching the npm script name only.
  pgrep -af 'npm run verify:contracts' 2>/dev/null | grep -v "$$" >/dev/null 2>&1
}

summarize_failures() {
  local log="$1"
  echo "---- failure excerpt (from ${log}) ----"
  rg -n 'FAIL |FAILED \(|ERROR:|File-size guardrails failed|ImportError|AssertionError|error TS|##\[error\]' "${log}" | tail -40 || true
  echo "---- end excerpt ----"
  echo "Full log: ${log}"
}

run_once() {
  local stamp head dirty_count
  stamp="$(date -Is)"
  head="$(git rev-parse --short HEAD 2>/dev/null || echo unknown)"
  dirty_count="$(git status --porcelain | wc -l | tr -d ' ')"

  {
    echo "=== change-verify-loop ${stamp} ==="
    echo "branch: $(git rev-parse --abbrev-ref HEAD)"
    echo "HEAD:   ${head} ($(git rev-parse HEAD))"
    echo "dirty:  ${dirty_count} paths (uncommitted)"
    echo "CRITICAL REVIEW CLAUSE (required before claiming green):"
    echo "  ${critical_review_clause}"
    echo
    git status -sb
    echo
  } | tee -a "${log_file}"

  if [[ "${dirty_count}" != "0" && "${head_only}" -eq 0 ]]; then
    {
      echo "NOTE: verifying DIRTY working tree, not the last pushed PR commit."
      echo "      GitHub Fast Gate green on HEAD does not clear these local edits."
      echo "      Use --head-only to verify the committed SHA only."
      git diff --stat || true
      echo
    } | tee -a "${log_file}"
  fi

  if other_verify_running; then
    {
      echo "SKIP: another npm run verify:contracts is already running."
      echo "      Wait for it (company agents / prior watch tick) or stop the duplicate."
      echo "VERIFY: SKIPPED (contention)"
    } | tee -a "${log_file}"
    return 2
  fi

  if [[ -f "${lock_file}" ]]; then
    local lock_pid
    lock_pid="$(cat "${lock_file}" 2>/dev/null || true)"
    if [[ -n "${lock_pid}" ]] && kill -0 "${lock_pid}" 2>/dev/null; then
      echo "SKIP: change-verify-loop already active (pid ${lock_pid})" | tee -a "${log_file}"
      return 2
    fi
  fi
  echo $$ >"${lock_file}"
  trap 'rm -f "${lock_file}"' EXIT

  local run_log="${log_dir}/verify-contracts-latest.log"
  echo "Running verify:contracts ... (log: ${run_log})" | tee -a "${log_file}"

  local stashed=0
  if [[ "${head_only}" -eq 1 && "${dirty_count}" != "0" ]]; then
    echo "Stashing dirty tree for --head-only verify..." | tee -a "${log_file}"
    git stash push -u -m "change-verify-loop --head-only ${stamp}" >/dev/null
    stashed=1
  fi

  set +e
  npm run verify:contracts >"${run_log}" 2>&1
  local rc=$?
  set -e

  if [[ "${stashed}" -eq 1 ]]; then
    git stash pop >/dev/null || {
      echo "WARN: stash pop had conflicts — resolve manually (git stash list)." | tee -a "${log_file}"
    }
  fi

  # Append a short tail into the rolling loop log.
  tail -n 30 "${run_log}" >>"${log_file}" || true

  if [[ "${rc}" -eq 0 ]]; then
    {
      echo
      echo "VERIFY: contracts PASSED (tree=$([[ ${dirty_count} == 0 || ${head_only} -eq 1 ]] && echo HEAD-commit || echo dirty-working-tree) head=${head})"
      echo "Confidence note: still require critical review of claims before merge."
    } | tee -a "${log_file}"
    return 0
  fi

  {
    echo
    echo "VERIFY: contracts FAILED (exit ${rc}) head=${head} dirty_paths=${dirty_count}"
    echo "Do not report bare FAILED — exact checks below:"
  } | tee -a "${log_file}"
  summarize_failures "${run_log}" | tee -a "${log_file}"
  return "${rc}"
}

if [[ "${watch_mode}" -eq 0 ]]; then
  run_once
  exit $?
fi

echo "Watching for git changes (Ctrl+C to stop)..."
echo "Logs: ${log_file}"
echo "      ${log_dir}/verify-contracts-latest.log"
prev=""
while true; do
  cur="$(fingerprint)"
  if [[ "${cur}" != "${prev}" ]]; then
    prev="${cur}"
    run_once || true
  fi
  sleep 20
done
