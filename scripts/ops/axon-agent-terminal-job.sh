#!/usr/bin/env bash
# Enqueue an Axon-owned agent-terminal job (live PTY + optional chat :::terminal tee).
# Prefer this over Cursor shellToolCall for OTA / EAS / Expo export so the console
# can stream mid-run output.
#
# Usage:
#   axon-agent-terminal-job [--workspace ID] [--no-stream] -- <command...>
#   axon-agent-terminal-job --status <job_id> --workspace ID
#   AXON_WATCH_WORKSPACE_ID=workspace_dashpro axon-agent-terminal-job -- npm run ota:canary
#
# From DashPro (or any bound project cwd), prefer the PATH name installed by
# ./scripts/ops/install-bin-wrappers.sh — relative ./scripts/ops/... under DashPro will fail.
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cp_base="${AXON_WATCH_CONTROL_PLANE_URL:-http://127.0.0.1:8787}"
workspace_id="${AXON_WATCH_WORKSPACE_ID:-}"
source_workspace_id="${AXON_AGENT_SOURCE_WORKSPACE_ID:-${AXON_WATCH_WORKSPACE_ID:-}}"
stream_to_chat="true"
run_id="${AXON_WATCH_RUN_ID:-}"
status_job_id=""

usage() {
  sed -n '2,12p' "$0" | sed 's/^# \{0,1\}//'
  exit 2
}

resolve_workspace_from_cwd() {
  local cwd bindings
  cwd="$(pwd -P)"
  bindings="${AXON_WATCH_PROJECT_BINDINGS:-${repo_root}/config/workspace-project-bindings.json}"
  if [[ -f "${bindings}" ]] && command -v jq >/dev/null 2>&1; then
    jq -r --arg cwd "${cwd}" '
      .bindings
      | to_entries
      | map(select(
          ($cwd == .value.project_root)
          or ($cwd | startswith(.value.project_root + "/"))
        ))
      | sort_by(.value.project_root | length)
      | reverse
      | .[0].key // empty
    ' "${bindings}"
  fi
}

encode_workspace() {
  python3 -c 'import urllib.parse,sys; print(urllib.parse.quote(sys.argv[1], safe=""))' "$1"
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --workspace)
      workspace_id="${2:-}"
      shift 2
      ;;
    --no-stream)
      stream_to_chat="false"
      shift
      ;;
    --run-id)
      run_id="${2:-}"
      shift 2
      ;;
    --status)
      status_job_id="${2:-}"
      shift 2
      ;;
    -h|--help)
      usage
      ;;
    --)
      shift
      break
      ;;
    *)
      break
      ;;
  esac
done

if [[ -z "${workspace_id}" ]]; then
  workspace_id="$(resolve_workspace_from_cwd || true)"
fi

if [[ -z "${workspace_id}" ]]; then
  echo "workspace_id required (pass --workspace or set AXON_WATCH_WORKSPACE_ID)" >&2
  exit 1
fi

encoded_workspace="$(encode_workspace "${workspace_id}")"

if [[ -n "${status_job_id}" ]]; then
  response="$(
    curl -sS \
      "${cp_base}/api/workspaces/${encoded_workspace}/terminal/agent-jobs/$(encode_workspace "${status_job_id}")"
  )"
  echo "${response}" | jq .
  status="$(echo "${response}" | jq -r '.status // empty')"
  if [[ -z "${status}" ]]; then
    echo "status lookup failed: ${response}" >&2
    exit 1
  fi
  exit 0
fi

if [[ $# -lt 1 ]]; then
  echo "command is required (or pass --status <job_id>)" >&2
  usage
fi

command="$*"

payload="$(
  jq -n \
    --arg command "${command}" \
    --argjson stream "${stream_to_chat}" \
    --arg run_id "${run_id}" \
    --arg source_workspace_id "${source_workspace_id}" \
    '{
      command: $command,
      stream_to_chat: $stream
    }
    + (if $run_id == "" then {} else {run_id: $run_id} end)
    + (if $source_workspace_id == "" then {} else {source_workspace_id: $source_workspace_id} end)'
)"

response="$(
  curl -sS -X POST \
    "${cp_base}/api/workspaces/${encoded_workspace}/terminal/agent-jobs" \
    -H 'Content-Type: application/json' \
    -d "${payload}"
)"

echo "${response}" | jq -r '
  "job_id=" + (.job_id // "?")
  + "\nstatus=" + (.status // "?")
  + "\nsession_id=" + (.session_id // "?")
  + "\nstream_to_chat=" + ((.stream_to_chat // false) | tostring)
  + "\n" + (.receipt // "")
'

job_id="$(echo "${response}" | jq -r '.job_id // empty')"
if [[ -z "${job_id}" ]]; then
  echo "enqueue failed: ${response}" >&2
  exit 1
fi
