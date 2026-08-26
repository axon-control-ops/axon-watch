#!/usr/bin/env bash
# Verify MoveIT service bridge using control-plane live_verify_commands.
# Usage: axon-agent-terminal-job --workspace MoveIT -- bash scripts/integrations/verify-service-bridge.sh
set -euo pipefail

API_BASE="${AXON_CONTROL_PLANE:-http://127.0.0.1:8787}"
WS="MoveIT"
FAIL=0

pass() { printf 'PASS  %s\n' "$1"; }
fail() { printf 'FAIL  %s\n' "$1"; FAIL=1; }

SC=$(curl -sf "${API_BASE}/api/workspaces/${WS}/service-connection")
READY=$(printf '%s' "$SC" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("ready", False))')
CONFIGURED=$(printf '%s' "$SC" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("configured", False))')

if [ "$CONFIGURED" = "True" ]; then
  pass "service-connection configured"
else
  fail "service-connection not configured"
fi

if [ "$READY" = "True" ]; then
  pass "service-connection ready"
else
  fail "service-connection not ready"
fi

COMMANDS=$(printf '%s' "$SC" | python3 -c '
import json, sys
data = json.load(sys.stdin)
for cmd in data.get("live_verify_commands", []):
    print("\t".join(cmd))
')

while IFS=$'\t' read -r -a CMD; do
  LABEL="${CMD[*]}"
  if "${CMD[@]}" >/dev/null 2>&1; then
    pass "live verify: ${LABEL}"
  else
    fail "live verify: ${LABEL}"
  fi
done <<< "$COMMANDS"

exit "$FAIL"
