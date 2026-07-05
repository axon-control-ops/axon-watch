"""P-C3 mobile operator cockpit compactness parity tests."""

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


def _watch_probe_ok() -> tuple[bool, str, None, str]:
    return (True, "ok", None, "2026-07-05T10:00:00Z")


class ParityC3MobileCompactViewportTests(unittest.TestCase):
    def setUp(self) -> None:
        isolate_control_plane_db(self, run_store)
        self.client = TestClient(app)
        self.addCleanup(self.client.close)

    def test_default_verify_wiring_includes_parity_c3_tests(self) -> None:
        package = json.loads((REPO_ROOT / "package.json").read_text(encoding="utf-8"))
        verify_script = package["scripts"]["verify:contracts"]
        self.assertIn("tests.test_parity_c3_mobile_compact_viewport", verify_script)

    def test_viewport_compact_query_toggles_server_compact_layout(self) -> None:
        with patch(
            "app.runtime_summary_assembler.default_watch_probe",
            return_value=_watch_probe_ok(),
        ):
            compact = self.client.get("/api/briefing?viewport_compact=true").json()
            standard = self.client.get("/api/briefing").json()

        self.assertTrue(compact["operator_presence"]["mobile"]["compact_layout"])
        self.assertFalse(standard["operator_presence"]["mobile"]["compact_layout"])
        self.assertTrue(compact["operator_presence"]["mobile"]["foreground_only"])
        self.assertEqual(compact["notice"], standard["notice"])
        self.assertEqual(compact["advise"], standard["advise"])

    def test_mobile_presence_keeps_foreground_only_honest_posture(self) -> None:
        with patch(
            "app.runtime_summary_assembler.default_watch_probe",
            return_value=_watch_probe_ok(),
        ):
            payload = self.client.get("/api/briefing?viewport_compact=true").json()

        mobile = payload["operator_presence"]["mobile"]
        self.assertTrue(mobile["foreground_only"])
        self.assertTrue(mobile["compact_layout"])


if __name__ == "__main__":
    unittest.main()
