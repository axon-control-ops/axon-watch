#!/usr/bin/env bash
# Portable launcher for the axon-research MCP server (no machine-absolute paths).
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
export PYTHONPATH="${ROOT}/services/control-plane${PYTHONPATH:+:${PYTHONPATH}}"
# Ensure Google CSE / research knobs from local .env reach this process.
if [[ -f "${ROOT}/.env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "${ROOT}/.env"
  set +a
fi
PYTHON_BIN="${ROOT}/.venv/bin/python3"
if [[ ! -x "${PYTHON_BIN}" ]]; then
  PYTHON_BIN="$(command -v python3)"
fi
exec "${PYTHON_BIN}" -m app.research.mcp_server "$@"
