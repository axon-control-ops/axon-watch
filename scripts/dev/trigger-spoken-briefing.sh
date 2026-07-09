#!/usr/bin/env bash
# Push a spoken-briefing SSE event to every connected console tab (IDE or operator).
set -euo pipefail

CP="${AXON_WATCH_CONTROL_PLANE_BASE:-http://127.0.0.1:8787}"

response="$(curl -fsS -X POST "${CP}/api/dev/trigger-spoken-briefing")"
echo "${response}"
subscribers="$(printf '%s' "${response}" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("subscribers", 0))')"
if [[ "${subscribers}" == "0" ]]; then
  echo "warning: no live-event subscribers — open :4173 and stay in IDE mode, then retry" >&2
  exit 1
fi
