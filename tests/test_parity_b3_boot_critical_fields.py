"""P-B3 runtime summary boot-critical field allowlist tests."""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.verify.check_runtime_summary_boot_fields import validate_boot_critical_fields

REPO_ROOT = Path(__file__).resolve().parents[1]
CONTRACT_FIXTURE = REPO_ROOT / "packages/shared-types/fixtures/runtime-summary.example.json"
SPEC_PATH = REPO_ROOT / "config/runtime-summary-boot-critical-fields.json"

CONTROL_PLANE_ROOT = REPO_ROOT / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.main import app  # noqa: E402
from app.runtime_summary_assembler import assemble_runtime_summary  # noqa: E402

from fastapi.testclient import TestClient  # noqa: E402


def _watch_probe_ok() -> tuple[bool, str, None, str]:
    return (True, "ok", None, "2026-07-05T10:00:00Z")


def _watch_inbox() -> dict[str, object]:
    return {
        "updated_at": "2026-07-05T10:00:00Z",
        "items": [
            {
                "signal_id": "signal_boot_fields",
                "severity": "high",
                "status": "open",
            }
        ],
    }


def _watch_summary() -> dict[str, object]:
    return {
        "updated_at": "2026-07-05T10:00:00Z",
        "connectors": {
            "configured": 1,
            "ok": 1,
            "degraded": 0,
            "unavailable": 0,
            "required_unavailable": 0,
        },
    }


class ParityB3BootCriticalFieldsTests(unittest.TestCase):
    def test_contract_fixture_matches_allowlist(self) -> None:
        payload = json.loads(CONTRACT_FIXTURE.read_text(encoding="utf-8"))
        spec = json.loads(SPEC_PATH.read_text(encoding="utf-8"))
        result = validate_boot_critical_fields(payload, spec=spec)
        self.assertEqual("pass", result.status)

    def test_assembler_output_matches_allowlist(self) -> None:
        payload = assemble_runtime_summary(
            watch_probe=_watch_probe_ok,
            inbox_fetcher=_watch_inbox,
            watch_summary_fetcher=_watch_summary,
        )
        spec = json.loads(SPEC_PATH.read_text(encoding="utf-8"))
        result = validate_boot_critical_fields(payload, spec=spec)
        self.assertEqual("pass", result.status)

    def test_runtime_summary_api_matches_allowlist(self) -> None:
        client = TestClient(app)
        self.addCleanup(client.close)
        with patch(
            "app.runtime_summary_assembler.default_watch_probe",
            return_value=_watch_probe_ok(),
        ), patch(
            "app.runtime_summary_assembler.fetch_watch_inbox",
            return_value=_watch_inbox(),
        ), patch(
            "app.runtime_summary_assembler.fetch_watch_summary",
            return_value=_watch_summary(),
        ):
            response = client.get("/api/runtime/summary")
        self.assertEqual(200, response.status_code)
        spec = json.loads(SPEC_PATH.read_text(encoding="utf-8"))
        result = validate_boot_critical_fields(response.json(), spec=spec)
        self.assertEqual("pass", result.status)


if __name__ == "__main__":
    unittest.main()
