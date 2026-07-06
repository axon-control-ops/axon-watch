from __future__ import annotations

import sys
import unittest
from pathlib import Path

WATCH_ROOT = Path(__file__).resolve().parents[1] / "services" / "axon-watch"
sys.path.insert(0, str(WATCH_ROOT))

from app.commands import store as command_store  # noqa: E402
from app.data.snapshot import operator_data_snapshot  # noqa: E402
from app.delivery import store as delivery_store  # noqa: E402
from app.events import store as event_store  # noqa: E402
from app.signals import suppression_store  # noqa: E402


class OperatorDataSnapshotTests(unittest.TestCase):
    def setUp(self) -> None:
        command_store.reset_store()
        event_store.reset_store()
        delivery_store.reset_store()
        suppression_store.reset_store()

    def test_snapshot_includes_all_watch_tables(self) -> None:
        command_store.save_command(
            {
                "command_id": "cmd-1",
                "command_type": "probe",
                "status": "completed",
                "updated_at": "2026-07-06T05:00:00Z",
            },
        )
        event_store.append_event(event_type="command.completed", command_id="cmd-1")
        delivery_store.append_receipt(
            signal_id="sig-1",
            event_id="event-1",
            channel="inbox",
            result="succeeded",
        )
        suppression_store.acknowledge_signals(["sig-1"], acknowledged_by="operator")

        snapshot = operator_data_snapshot(limit=10)
        tables = snapshot["tables"]
        self.assertEqual(1, tables["commands"]["total"])
        self.assertEqual(1, tables["events"]["total"])
        self.assertEqual(1, tables["receipts"]["total"])
        self.assertEqual(1, tables["suppressions"]["total"])


if __name__ == "__main__":
    unittest.main()
