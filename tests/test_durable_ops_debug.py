"""Restart-safe durable ops + monitor/debug adapter tests."""

from __future__ import annotations

import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.workspace_agents.durable_ops import (  # noqa: E402
    FairSchedulerControls,
    IdempotentEffectLedger,
    RestartSafeLeaseManager,
)
from app.workspace_agents.monitor_debug import (  # noqa: E402
    IncidentSignal,
    incident_to_debug_task,
    signal_clear_proof,
)


class DurableOpsTests(unittest.TestCase):
    def test_effect_ledger_is_idempotent(self) -> None:
        ledger = IdempotentEffectLedger()
        first, receipt = ledger.claim("pr:task1", "open_pr", "abc")
        second, again = ledger.claim("pr:task1", "open_pr", "abc")
        self.assertTrue(first)
        self.assertFalse(second)
        self.assertEqual(receipt.effect_key, again.effect_key)

    def test_lease_recovers_after_expiry(self) -> None:
        mgr = RestartSafeLeaseManager()
        now = datetime(2026, 7, 23, 12, 0, tzinfo=timezone.utc)
        mgr.acquire("task_a", "worker-1", ttl_seconds=30, now=now)
        recovered = mgr.recover_expired(now=now + timedelta(seconds=31))
        self.assertEqual(["task_a"], recovered)
        lease = mgr.acquire("task_a", "worker-2", ttl_seconds=30, now=now + timedelta(seconds=32))
        self.assertEqual("worker-2", lease.holder)

    def test_fair_capacity_backoff_and_stop(self) -> None:
        controls = FairSchedulerControls()
        ok, reason = controls.can_dispatch("proj")
        self.assertTrue(ok)
        controls.mark_dispatch("proj")
        controls.mark_dispatch("proj")
        ok, reason = controls.can_dispatch("proj")
        self.assertFalse(ok)
        self.assertEqual("capacity", reason)
        controls.dead_letter("proj", "task_x")
        controls.backoff("proj", seconds=60)
        ok, reason = controls.can_dispatch("proj")
        self.assertFalse(ok)
        controls.operator_stop("proj")
        ok, reason = controls.can_dispatch("proj")
        self.assertEqual("operator_stop", reason)


class MonitorDebugTests(unittest.TestCase):
    def test_incident_becomes_evidence_linked_task(self) -> None:
        contract = {
            "certification_level": "monitor_debug",
            "health_probes": ["http://127.0.0.1:8787/healthz"],
            "observability": {"logs": ["logs/"], "metrics": [], "traces": []},
            "verifier": {"required_checks": ["test", "security"]},
        }
        signal = IncidentSignal(
            source="sentry",
            severity="high",
            message="NullPointer in payments",
            fingerprint="fp-1",
            evidence_uris=["sentry://event/1"],
        )
        plan = incident_to_debug_task(signal, contract=contract)
        self.assertIn("fp-1", plan.acceptance_criteria)
        self.assertEqual(["test", "security"], plan.verifier_checks)
        proof = signal_clear_proof(fingerprint="fp-1", remaining_signals=[])
        self.assertTrue(proof["cleared"])


if __name__ == "__main__":
    unittest.main()
