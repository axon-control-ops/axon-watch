#!/usr/bin/env bash
# Lead fan-out: decompose a goal into role-scoped tasks and dispatch teammates.
#
# Without this, a Lead can describe a handoff in a document but has no approved
# way to reach the control plane, so nobody is actually dispatched.
#
# Usage:
#   axon-assign [--workspace ID] [--mode auto|fan_out|sequential|decompose] \
#               [--no-runs] -- <goal...>
#   axon-assign --workspace workspace_dashpro -- Fix red CI on development
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cp_base="${AXON_WATCH_CONTROL_PLANE_URL:-http://127.0.0.1:8787}"
workspace_id="${AXON_WATCH_WORKSPACE_ID:-}"
mode="auto"
create_runs="true"

usage() {
  sed -n '2,10p' "$0" | sed 's/^# \{0,1\}//'
  exit 2
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --workspace) workspace_id="${2:-}"; shift 2 ;;
    --mode) mode="${2:-auto}"; shift 2 ;;
    --no-runs) create_runs="false"; shift ;;
    -h|--help) usage ;;
    --) shift; break ;;
    *) break ;;
  esac
done

if [[ -z "${workspace_id}" ]]; then
  echo "workspace_id required (pass --workspace or set AXON_WATCH_WORKSPACE_ID)" >&2
  exit 1
fi
if [[ $# -lt 1 ]]; then
  echo "goal is required" >&2
  usage
fi

goal="$*"
encoded_workspace="$(python3 -c 'import urllib.parse,sys; print(urllib.parse.quote(sys.argv[1], safe=""))' "${workspace_id}")"

payload="$(
  jq -n --arg goal "${goal}" --arg mode "${mode}" --argjson runs "${create_runs}" \
    '{goal: $goal, mode: $mode, create_runs: $runs}'
)"

auth_args=()
if [[ -n "${AXON_WATCH_OPERATOR_TOKEN:-}" ]]; then
  auth_args=(-H "Authorization: Bearer ${AXON_WATCH_OPERATOR_TOKEN}")
fi

response="$(
  curl -sS -X POST \
    "${cp_base}/api/workspaces/${encoded_workspace}/lead/fan-out" \
    -H 'Content-Type: application/json' \
    "${auth_args[@]}" \
    -d "${payload}"
)"

echo "${response}" | jq .
if [[ -z "$(echo "${response}" | jq -r '.tasks // .items // empty')" ]]; then
  echo "fan-out returned no tasks: ${response}" >&2
  exit 1
fi
