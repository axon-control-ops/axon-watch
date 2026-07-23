"""P-C4 spoken high-value alerts parity tests."""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from tests.support.control_plane_db import isolate_control_plane_db

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.main import app  # noqa: E402
from app.persistence import run_store  # noqa: E402
from app.runs.service import create_run  # noqa: E402
from app.spoken_alert_policy import clear_spoken_alert_dedupe_for_tests  # noqa: E402


def _watch_probe_ok() -> tuple[bool, str, None, str]:
    return (True, "ok", None, "2026-07-05T10:00:00Z")


class ParityC4SpokenHighValueAlertsTests(unittest.TestCase):
    def setUp(self) -> None:
        clear_spoken_alert_dedupe_for_tests()
        isolate_control_plane_db(self, run_store)
        self.client = TestClient(app)
        self.addCleanup(self.client.close)

    def _briefing_with_probe(self) -> dict[str, object]:
        with patch(
            "app.runtime_summary_assembler.default_watch_probe",
            return_value=_watch_probe_ok(),
        ):
            response = self.client.get("/api/briefing")
        self.assertEqual(200, response.status_code)
        return response.json()

    def test_default_verify_wiring_includes_parity_c4_tests(self) -> None:
        from tests.verify_contract_wiring import contract_verify_wiring_surface

        verify_script = contract_verify_wiring_surface()
        self.assertIn("tests.test_parity_c4_spoken_high_value_alerts", verify_script)

    def test_pending_approval_marks_spoken_alert_eligible(self) -> None:
        create_run(
            workspace_id="workspace_smoke",
            mode="agent",
            summary="P-C4 spoken alert parity run",
            requires_approval=True,
        )
        payload = self._briefing_with_probe()
        spoken = payload["operator_presence"]["spoken_alert"]

        self.assertTrue(spoken["eligible"])
        self.assertEqual("operator_approval_required", spoken["reason"])
        self.assertTrue(str(spoken["message"]).strip())

    def test_persisted_spoken_alerts_disable_blocks_eligibility(self) -> None:
        create_run(
            workspace_id="workspace_smoke",
            mode="agent",
            summary="P-C4 spoken toggle run",
            requires_approval=True,
        )
        enabled = self._briefing_with_probe()
        self.assertTrue(enabled["operator_presence"]["spoken_alert"]["eligible"])

        response = self.client.put(
            "/api/operator-presence/settings",
            json={"spoken_alerts_enabled": False},
        )
        self.assertEqual(200, response.status_code)

        disabled = self._briefing_with_probe()
        spoken = disabled["operator_presence"]["spoken_alert"]
        self.assertFalse(spoken["eligible"])
        self.assertEqual("spoken_alerts_disabled", spoken["reason"])
        self.assertEqual("", spoken["message"])
        self.assertEqual(
            enabled["pending_approvals"]["count"],
            disabled["pending_approvals"]["count"],
        )

    def test_privacy_mode_blocks_spoken_alert_without_changing_truth(self) -> None:
        create_run(
            workspace_id="workspace_smoke",
            mode="agent",
            summary="P-C4 privacy spoken run",
            requires_approval=True,
        )
        self.client.put("/api/operator-presence/settings", json={"privacy_mode": True})
        payload = self._briefing_with_probe()
        spoken = payload["operator_presence"]["spoken_alert"]

        self.assertFalse(spoken["eligible"])
        self.assertEqual("privacy_mode_active", spoken["reason"])
        self.assertGreater(payload["pending_approvals"]["count"], 0)

    def test_contract_fixture_passes_spoken_alert_checker(self) -> None:
        from scripts.verify.check_spoken_alert_policy import validate_spoken_alert

        fixture = REPO_ROOT / "packages/shared-types/fixtures/operator-briefing.example.json"
        payload = json.loads(fixture.read_text(encoding="utf-8"))
        result = validate_spoken_alert(payload)
        self.assertEqual("pass", result.status)


if __name__ == "__main__":
    unittest.main()
