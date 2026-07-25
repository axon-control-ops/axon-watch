#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${repo_root}"

echo "P-D1: watch SQLite persistence parity gate"
echo

echo "[1/7] Parity closure order validation"
python3 ./scripts/verify/check_parity_closure.py
echo

echo "[2/7] P-D1 watch persistence integration tests"
python3 -m unittest tests.test_parity_d1_watch_persistence -v
echo

echo "[3/7] Watch commands/events regression"
python3 -m unittest tests.test_watch_commands_events tests.test_control_plane_watch_commands -v
echo

echo "[4/7] Delivery receipts regression"
python3 -m unittest tests.test_watch_delivery_receipts tests.test_control_plane_delivery_receipts -v
echo

echo "[5/7] SQLite schema + store modules present"
python3 - <<'PY'
from pathlib import Path
for path in (
    "services/axon-watch/app/persistence/watch_store_sqlite.py",
    "services/axon-watch/app/commands/store.py",
    "services/axon-watch/app/events/store.py",
    "services/axon-watch/app/delivery/store.py",
):
    if not Path(path).is_file():
        raise SystemExit(f"missing {path}")
text = Path("services/axon-watch/app/commands/store.py").read_text(encoding="utf-8")
if "watch_store_sqlite" not in text:
    raise SystemExit("commands store not wired to SQLite")
print("watch SQLite persistence modules present")
PY
echo

echo "[6/7] P-D1 slice spec present"
test -f docs/PARITY_D1_WATCH_PERSISTENCE.md
echo "  ok docs/PARITY_D1_WATCH_PERSISTENCE.md"
echo

echo "[7/7] Full verify gate"
npm run verify
echo

echo "P-D1 PASS"
