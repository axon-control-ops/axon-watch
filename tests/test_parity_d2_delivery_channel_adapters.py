"""P-D2 delivery channel adapter parity tests."""

from __future__ import annotations

import json
import os
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from tests.support.watch_app_loader import load_watch_app, restore_app_modules
from tests.support.watch_db import isolate_watch_db

REPO_ROOT = Path(__file__).resolve().parents[1]


class ParityD2DeliveryChannelAdapterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_state = Path(self._enter_temp_state())
        isolate_watch_db(self)
        self.env_patch = patch.dict(
            os.environ,
            {
                "AXON_WATCH_STATE_DIR": str(self.temp_state),
                "AXON_WATCH_DELIVERY_WEBHOOK_URL": "http://127.0.0.1:9999/delivery",
                "AXON_WATCH_DELIVERY_RETRY_MAX": "3",
            },
            clear=False,
        )
        self.env_patch.start()
        self.addCleanup(self.env_patch.stop)

        watch_app, self._watch_modules = load_watch_app()
        from app.delivery import store as delivery_store  # noqa: WPS433
        from app.events import store as event_store  # noqa: WPS433

        delivery_store.reset_store()
        event_store.reset_store()
        self.client = TestClient(watch_app)
        self.addCleanup(self.client.close)

    def _enter_temp_state(self) -> str:
        import tempfile

        tempdir = tempfile.mkdtemp()
        self.addCleanup(lambda: __import__("shutil").rmtree(tempdir, ignore_errors=True))
        return tempdir

    def tearDown(self) -> None:
        restore_app_modules(self._watch_modules)

    def test_default_verify_wiring_includes_parity_d2_tests(self) -> None:
        from tests.verify_contract_wiring import contract_verify_wiring_surface

        verify_script = contract_verify_wiring_surface()
        self.assertIn("tests.test_parity_d2_delivery_channel_adapters", verify_script)

    def test_high_signal_uses_desktop_file_and_webhook_adapters(self) -> None:
        attempts = {"count": 0}

        def fake_post(url: str, payload: dict[str, object], *, timeout_seconds: float = 5.0) -> None:
            _ = timeout_seconds
            attempts["count"] += 1
            self.assertEqual("http://127.0.0.1:9999/delivery", url)
            self.assertTrue(str(payload.get("signal_id", "")).startswith("signal_"))

        with patch("app.delivery.adapters.webhook.post_json", side_effect=fake_post):
            response = self.client.get("/internal/watch/inbox")

        self.assertEqual(200, response.status_code)
        degraded = next(
            row
            for row in response.json()["items"]
            if row["signal_id"] == "signal_runtime_summary_degraded"
        )
        self.assertEqual("delivered", degraded["delivery_state"])
        self.assertGreaterEqual(int(degraded.get("delivery_receipt_count", 0)), 3)

        receipts = self.client.get("/internal/watch/delivery/receipts?limit=20").json()["items"]
        by_channel = {row["channel"]: row for row in receipts if row["signal_id"] == degraded["signal_id"]}
        self.assertEqual("succeeded", by_channel["desktop"]["result"])
        self.assertEqual("desktop_notification_recorded", by_channel["desktop"]["policy_reason"])
        self.assertEqual("succeeded", by_channel["webhook"]["result"])
        self.assertEqual("webhook_delivered", by_channel["webhook"]["policy_reason"])
        self.assertGreaterEqual(attempts["count"], 1)

        desktop_path = self.temp_state / "desktop-notifications.jsonl"
        self.assertTrue(desktop_path.is_file())
        desktop_lines = desktop_path.read_text(encoding="utf-8").strip().splitlines()
        desktop_payloads = [json.loads(line) for line in desktop_lines]
        degraded_desktop = next(
            row for row in desktop_payloads if row["signal_id"] == "signal_runtime_summary_degraded"
        )
        self.assertEqual("Bootstrap: runtime summary stale", degraded_desktop["title"])

    def test_contract_checker_passes_adapter_layout(self) -> None:
        from scripts.verify.check_delivery_channel_adapters import validate_delivery_adapters

        result = validate_delivery_adapters()
        self.assertEqual("pass", result.status)


if __name__ == "__main__":
    unittest.main()
