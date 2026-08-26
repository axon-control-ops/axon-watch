#!/usr/bin/env bash
# MoveIT workspace health probe — Watcher guardrail
# Usage: axon-agent-terminal-job --workspace MoveIT -- bash scripts/guardrails/check-workspace-health.sh
set -euo pipefail

API_BASE="${AXON_CONTROL_PLANE:-http://127.0.0.1:8787}"
WS="MoveIT"
FAIL=0
CURL_OPTS=(--max-time 10)

pass() { printf 'PASS  %s\n' "$1"; }
fail() { printf 'FAIL  %s\n' "$1"; FAIL=1; }
warn() { printf 'WARN  %s\n' "$1"; }

# Workspace record
if curl "${CURL_OPTS[@]}" -sf "${API_BASE}/api/workspaces/${WS}" >/dev/null; then
  pass "workspace record reachable"
else
  fail "workspace record unreachable at ${API_BASE}"
fi

# Service connection
SC=$(curl "${CURL_OPTS[@]}" -sf "${API_BASE}/api/workspaces/${WS}/service-connection" 2>/dev/null || echo '{}')
SC_HINT=$(printf '%s' "$SC" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("hint", ""))' 2>/dev/null || true)
if echo "$SC" | grep -q '"configured":true'; then
  pass "service-connection configured"
else
  fail "service-connection not configured"
fi
if echo "$SC" | grep -q '"ready":true'; then
  pass "service-connection ready"
else
  fail "service-connection not ready${SC_HINT:+ - ${SC_HINT}}"
fi

# Git presence
if [ -d .git ]; then
  pass "git repository present"
else
  fail "no .git in project root"
fi

# Package manifest
if [ -f package.json ]; then
  pass "package.json is a file"
else
  fail "package.json missing or not a file"
fi

# Smoke tests
if [ -f package.json ] && npm test >/dev/null 2>&1; then
  pass "npm test passes"
else
  fail "npm test fails"
fi

# Terminal wrapper
if command -v axon-agent-terminal-job >/dev/null 2>&1; then
  pass "axon-agent-terminal-job available"
else
  fail "axon-agent-terminal-job not on PATH"
fi

# Workspace delivery config (publish gate)
DELIVERY_HTTP=$(curl "${CURL_OPTS[@]}" -s -o /tmp/moveit-delivery.json -w '%{http_code}' "${API_BASE}/api/workspaces/${WS}/delivery" 2>/dev/null || echo "000")
if [ "$DELIVERY_HTTP" = "200" ]; then
  pass "workspace delivery endpoint reachable"
else
  fail "workspace delivery not configured (HTTP ${DELIVERY_HTTP}) — continuous publish blocked"
fi

# Handoff delivery status (informational)
HANDOFFS=$(curl "${CURL_OPTS[@]}" -sf "${API_BASE}/api/workspaces/${WS}/handoffs" 2>/dev/null || echo '{"items":[]}')
if echo "$HANDOFFS" | grep -q '"status":"failed"'; then
  warn "one or more historical handoffs failed — review before relying on past publish attempts"
fi

exit "$FAIL"
