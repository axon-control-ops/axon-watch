#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${repo_root}"

echo "TEST-10: final parity verification and cutover decision gate"
echo

echo "[1/6] Parity snapshot validation"
python3 ./scripts/verify/check_parity_snapshot.py
echo

echo "[2/6] Parity snapshot unit tests"
python3 -m unittest tests.test_parity_snapshot -v
echo

echo "[3/6] Final parity acceptance tests"
python3 -m unittest tests.test_test10_final_parity_acceptance -v
echo

echo "[4/6] Prior cutover gate scripts present and executable"
for index in $(seq 0 9); do
  script="./scripts/verify/test${index}-"
  case "${index}" in
    0) script+="workspace-smoke.sh" ;;
    1) script+="workspace-project-connection.sh" ;;
    2) script+="workspace-handoff.sh" ;;
    3) script+="watch-connectors.sh" ;;
    4) script+="watch-command-event-depth.sh" ;;
    5) script+="delivery-receipts.sh" ;;
    6) script+="kairo-watch-rules.sh" ;;
    7) script+="operator-presence.sh" ;;
    8) script+="dedicated-server-readiness.sh" ;;
    9) script+="cross-repo-planning-migration.sh" ;;
  esac
  test -x "${script}"
  echo "  ok ${script}"
done
echo

echo "[5/6] Cutover decision document integrity"
python3 - <<'PY'
from pathlib import Path

decision = Path("docs/CUTOVER_DECISION.md").read_text(encoding="utf-8")
required = [
    "Bounded Axon-X cutover",
    "NOT APPROVED",
    "config/parity-snapshot.json",
    "verify:test10",
]
for token in required:
    if token not in decision:
        raise SystemExit(f"CUTOVER_DECISION.md missing: {token}")
print("cutover decision document ok")
PY
echo

echo "[6/6] Full verify gate"
npm run verify
echo

echo "TEST-10 PASS"
