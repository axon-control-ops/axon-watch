#!/usr/bin/env bash
# Watcher-only: look up another agent's run status and history.
#
# Recovery/diagnosis watchers are asked to explain a prior run's outcome, but
# acceptance_evidence, diff_budget findings, and review_ready/complete phase
# transitions are recorded only in the control-plane's run store -- never as
# files in the workspace checkout a watcher can read. Without this, a watcher
# can only ask the operator for "one authoritative pointer" it has no way to
# resolve itself and stalls out consultative-only.
#
# Materialized from the running control-plane package, not resolved through
# PATH -- see agent_sandbox.py's _builtin_wrapper_source for why (a PATH shim
# would be a dangling symlink inside Bubblewrap).
#
# Usage:
#   axon-runlog <run_id>
set -euo pipefail

cp_base="${AXON_WATCH_CONTROL_PLANE_URL:-http://127.0.0.1:8787}"

usage() {
  sed -n '2,15p' "$0" | sed 's/^# \{0,1\}//'
  exit 2
}

if [[ $# -lt 1 || "$1" == "-h" || "$1" == "--help" ]]; then
  usage
fi
run_id="$1"

auth_args=()
if [[ -n "${AXON_WATCH_OPERATOR_TOKEN:-}" ]]; then
  auth_args=(-H "Authorization: Bearer ${AXON_WATCH_OPERATOR_TOKEN}")
fi

run="$(curl -sS "${auth_args[@]}" "${cp_base}/api/runs/${run_id}")"

# GET /api/runs/{run_id} has no workspace scoping of its own (it backs the
# operator's cross-workspace dashboard), so this wrapper is the only boundary
# stopping a watcher from reading a DIFFERENT workspace's run/acceptance
# evidence if it ever learns that workspace's run_id. Enforce it here.
run_workspace="$(echo "${run}" | jq -r '.workspace_id // empty')"
if [[ -n "${AXON_WATCH_WORKSPACE_ID:-}" && -n "${run_workspace}" && "${run_workspace}" != "${AXON_WATCH_WORKSPACE_ID}" ]]; then
  echo "axon-runlog: run ${run_id} belongs to workspace '${run_workspace}', not this workspace ('${AXON_WATCH_WORKSPACE_ID}') -- refusing to read another workspace's run evidence" >&2
  exit 1
fi

history="$(curl -sS "${auth_args[@]}" "${cp_base}/api/runs/${run_id}/history")"

jq -n --argjson run "${run}" --argjson history "${history}" '{run: $run, history: $history}'
