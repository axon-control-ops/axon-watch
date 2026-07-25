#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${repo_root}"

echo "Headed browser smoke gate (:4173)"
echo

echo "[1/3] Dev stack health"
./scripts/dev/check-health.sh
echo

echo "[2/3] Playwright browser smoke (headless screenshots; AXON_HEADED=1 for visible browser)"
./scripts/dev/python.sh scripts/verify/headed_browser_smoke.py \
  --write-report "${repo_root}/.local/verify/headed-smoke/headed-browser-smoke-report.json"
echo

echo "[3/3] Manual operator reminder"
echo "  For Phase G6 dry-run, also verify in a visible browser when needed:"
echo "  - composer ArrowUp history, Resend, markdown Copy, Resume after error"
echo "  - log any forced :7734 fallback with blocker ID in docs/PHASE_G6_RETIREMENT_READINESS.md"
echo

echo "HEADED-BROWSER-SMOKE PASS"
