"""P-C1 KAIRO persona operator copy parity tests."""

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


def _watch_probe_ok() -> tuple[bool, str, None, str]:
    return (True, "ok", None, "2026-07-05T10:00:00Z")


class ParityC1PersonaSettingsTests(unittest.TestCase):
    def setUp(self) -> None:
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

    def test_default_verify_wiring_includes_parity_c1_tests(self) -> None:
        from tests.verify_contract_wiring import contract_verify_wiring_surface

        verify_script = contract_verify_wiring_surface()
        self.assertIn("tests.test_parity_c1_persona_settings", verify_script)

    def test_persisted_persona_disable_changes_tone_not_truth(self) -> None:
        create_run(
            workspace_id="workspace_smoke",
            mode="agent",
            summary="P-C1 persona parity run",
            requires_approval=True,
        )

        enabled = self._briefing_with_probe()
        self.assertGreater(enabled["pending_approvals"]["count"], 0)
        self.assertTrue(
            str(enabled["operator_presence"]["persona_voice_line"]).startswith("VAXON:")
        )

        response = self.client.put(
            "/api/operator-presence/settings",
            json={"operator_persona_enabled": False},
        )
        self.assertEqual(200, response.status_code)

        disabled = self._briefing_with_probe()
        voice_line = str(disabled["operator_presence"]["persona_voice_line"])
        self.assertNotIn("KAIRO", voice_line)
        lowered = voice_line.lower()
        self.assertTrue(
            "approval" in lowered or "approve" in lowered or "yes or no" in lowered,
            voice_line,
        )
        self.assertEqual(enabled["pending_approvals"]["count"], disabled["pending_approvals"]["count"])
        self.assertEqual(enabled["notice"], disabled["notice"])
        self.assertEqual(enabled["advise"], disabled["advise"])
        self.assertFalse(disabled["operator_presence"]["settings"]["operator_persona_enabled"])

    def test_settings_survive_subsequent_briefing_requests(self) -> None:
        self.client.put("/api/operator-presence/settings", json={"operator_persona_enabled": False})
        first = self._briefing_with_probe()
        second = self._briefing_with_probe()
        self.assertEqual(
            first["operator_presence"]["settings"],
            second["operator_presence"]["settings"],
        )
        self.assertNotIn("KAIRO", str(second["operator_presence"]["persona_voice_line"]))


if __name__ == "__main__":
    unittest.main()
