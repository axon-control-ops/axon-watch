#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${repo_root}"

source "${repo_root}/scripts/dev/lib/common.sh"
load_env
"${repo_root}/scripts/dev/ensure-python-deps.sh" >/dev/null 2>&1 || true
python_bin="$(resolve_python "${repo_root}")"

echo "research-lane-smoke: service + stream + prompt gates"
echo

echo "[1/3] Research service smoke"
./scripts/verify/research-smoke.sh
echo

echo "[2/3] Research stream block normalization"
PYTHONPATH=services/control-plane "${python_bin}" -m unittest \
  tests.test_cursor_stream_research_blocks \
  tests.test_research_mcp \
  -v
echo

echo "[3/3] Lane B prompt hardening"
PYTHONPATH=services/control-plane "${python_bin}" - <<'PY'
from app.research.availability import format_capability_line, research_capability_snapshot
from app.cli_runtime.router import _system_prompt

snapshot = research_capability_snapshot()
assert snapshot.get("available") is True, snapshot
line = format_capability_line(snapshot)
assert "axon_research_search" in line
assert "headless runtime" in line

agent_prompt = _system_prompt("agent", "executing", research_snapshot=snapshot)
assert "axon_research_search" in agent_prompt
assert "webSearch/webFetch" in agent_prompt

plan_prompt = _system_prompt("plan", "consultative", research_snapshot=snapshot)
assert "axon_research_search" in plan_prompt

print("prompt-hardening: ok")
PY

echo
echo "research-lane-smoke: ok"
