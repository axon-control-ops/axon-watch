"""Stale-decision expiry sweep for the Mission Control "Needs You" queue.

Regression coverage: pending_critical_decisions had no staleness/TTL
mechanism at all — critical_signal connector/monitor alerts and
operator_blocker failed-shift items just accumulated forever once created,
even after the underlying condition had obviously cleared (confirmed live:
a "Console web connector unavailable" alert from days earlier was still
"pending" while the connector had been reachable the entire time). Unlike
failed_shift items (which reconcile_recovered_failed_shift_decisions can
verify against a later successful run), most of these kinds have no cheap
re-probe available, so this is a conservative time-based fallback.
"""

from __future__ import annotations

import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from tests.support.control_plane_db import isolate_control_plane_db

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.persistence import autonomous_attention_store, task_store  # noqa: E402
from app.workspace_agents.autonomous_attention_recovery import (  # noqa: E402
    sweep_stale_attention_decisions,
)


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


class StaleAttentionSweepTests(unittest.TestCase):
    def setUp(self) -> None:
        isolate_control_plane_db(self, task_store)
        autonomous_attention_store.reset_store()

    def _add_pending(
        self,
        *,
        dedupe_key: str,
        created_at: datetime,
        title: str = "t",
        kind: str = "critical_signal",
    ) -> str:
        receipt = autonomous_attention_store.append_receipt(
            kind=kind, decision="escalate", tier="operator_gated",
            title=title, detail="d", dedupe_key=dedupe_key,
            workspace_id="workspace_axon_watch", ask_operator=True,
        )
        receipt_id = str(receipt["receipt_id"])
        # append_receipt always stamps "now" — backdate directly for the test.
        with autonomous_attention_store._managed_connection() as connection:
            autonomous_attention_store.ensure_autonomy_receipt_schema(connection)
            connection.execute(
                "UPDATE autonomy_attention_receipts SET created_at = ? WHERE receipt_id = ?",
                (_iso(created_at), receipt_id),
            )
            connection.commit()
        return receipt_id

    def test_old_item_with_no_recurrence_expires(self) -> None:
        now = datetime.now(timezone.utc)
        receipt_id = self._add_pending(
            dedupe_key="signal:workspace_axon_watch:signal_connector_console_web_unavailable:critical",
            created_at=now - timedelta(hours=48),
        )
        expired = sweep_stale_attention_decisions(max_age_hours=24.0, now=now)
        self.assertEqual([receipt_id], [str(r["receipt_id"]) for r in expired])
        receipt = autonomous_attention_store.get_receipt(receipt_id)
        assert receipt is not None
        self.assertEqual("resolved", receipt["status"])
        self.assertEqual("stale_expired", receipt["resolution"])

    def test_recent_item_is_not_touched(self) -> None:
        now = datetime.now(timezone.utc)
        receipt_id = self._add_pending(
            dedupe_key="failed_shift:workspace_dashpro:watcher",
            created_at=now - timedelta(hours=1),
        )
        expired = sweep_stale_attention_decisions(max_age_hours=24.0, now=now)
        self.assertEqual([], expired)
        receipt = autonomous_attention_store.get_receipt(receipt_id)
        assert receipt is not None
        self.assertEqual("pending", receipt["status"])

    def test_recurring_problem_is_not_expired_even_when_old(self) -> None:
        # An old item whose fingerprint has recurred MORE RECENTLY is still
        # an active, ongoing problem — must stay visible, not be silently
        # cleared just because the FIRST occurrence aged out.
        now = datetime.now(timezone.utc)
        old_id = self._add_pending(
            dedupe_key="failed_shift:workspace_dashpro:integrations",
            created_at=now - timedelta(hours=48),
        )
        recent_id = self._add_pending(
            dedupe_key="failed_shift:workspace_dashpro:integrations",
            created_at=now - timedelta(hours=1),
        )
        expired = sweep_stale_attention_decisions(max_age_hours=24.0, now=now)
        self.assertEqual([], expired)
        old_receipt = autonomous_attention_store.get_receipt(old_id)
        recent_receipt = autonomous_attention_store.get_receipt(recent_id)
        assert old_receipt is not None and recent_receipt is not None
        self.assertEqual("pending", old_receipt["status"])
        self.assertEqual("pending", recent_receipt["status"])

    def test_items_with_empty_dedupe_key_are_independently_eligible(self) -> None:
        now = datetime.now(timezone.utc)
        first_id = self._add_pending(dedupe_key="", created_at=now - timedelta(hours=48))
        second_id = self._add_pending(dedupe_key="", created_at=now - timedelta(hours=36))
        expired = sweep_stale_attention_decisions(max_age_hours=24.0, now=now)
        expired_ids = {str(r["receipt_id"]) for r in expired}
        self.assertEqual({first_id, second_id}, expired_ids)

    def test_custom_max_age_is_respected(self) -> None:
        now = datetime.now(timezone.utc)
        receipt_id = self._add_pending(
            dedupe_key="signal:x", created_at=now - timedelta(hours=3),
        )
        self.assertEqual([], sweep_stale_attention_decisions(max_age_hours=24.0, now=now))
        expired = sweep_stale_attention_decisions(max_age_hours=1.0, now=now)
        self.assertEqual([receipt_id], [str(r["receipt_id"]) for r in expired])

    def test_already_resolved_items_are_ignored(self) -> None:
        now = datetime.now(timezone.utc)
        receipt_id = self._add_pending(
            dedupe_key="signal:y", created_at=now - timedelta(hours=48),
        )
        autonomous_attention_store.resolve_decision(receipt_id, resolution="approved")
        expired = sweep_stale_attention_decisions(max_age_hours=24.0, now=now)
        self.assertEqual([], expired)


if __name__ == "__main__":
    unittest.main()
