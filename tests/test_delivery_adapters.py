"""Unit tests for delivery channel adapters."""

from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tests.support.watch_app_loader import load_watch_app, restore_app_modules


class DeliveryAdapterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._watch_app, cls._watch_modules = load_watch_app()

    @classmethod
    def tearDownClass(cls) -> None:
        restore_app_modules(cls._watch_modules)

    def test_inbox_adapter_succeeds(self) -> None:
        from app.delivery.adapters.inbox import deliver_inbox  # noqa: WPS433

        result, error, reason = deliver_inbox(
            item={"title": "Watch summary degraded"},
            signal_id="signal_x",
        )
        self.assertEqual(("succeeded", "", "inbox_projection_available"), (result, error, reason))

    def test_desktop_adapter_writes_notification_file(self) -> None:
        from app.delivery.adapters.desktop import deliver_desktop  # noqa: WPS433

        with tempfile.TemporaryDirectory() as tempdir:
            notify_path = Path(tempdir) / "desktop.jsonl"
            with patch.dict(
                os.environ,
                {"AXON_WATCH_DESKTOP_NOTIFY_PATH": str(notify_path)},
                clear=False,
            ):
                result, error, reason = deliver_desktop(
                    item={
                        "title": "Watch summary degraded",
                        "summary": "Watch summary is degraded.",
                        "severity": "high",
                    },
                    signal_id="signal_runtime_summary_degraded",
                )
            self.assertEqual("succeeded", result)
            self.assertEqual("", error)
            self.assertEqual("desktop_notification_recorded", reason)
            lines = notify_path.read_text(encoding="utf-8").strip().splitlines()
            self.assertEqual(1, len(lines))
            payload = json.loads(lines[0])
            self.assertEqual("signal_runtime_summary_degraded", payload["signal_id"])

    def test_webhook_adapter_requires_configuration(self) -> None:
        from app.delivery.adapters.webhook import deliver_webhook  # noqa: WPS433

        with patch.dict(os.environ, {}, clear=True):
            result, error, reason = deliver_webhook(item={"title": "x"}, signal_id="signal_x")
        self.assertEqual("failed", result)
        self.assertIn("not configured", error.lower())
        self.assertEqual("channel_not_configured", reason)

    def test_registry_retries_configured_webhook(self) -> None:
        from app.delivery.adapters.registry import attempt_channel_delivery  # noqa: WPS433

        attempts = {"count": 0}

        def fake_post(url: str, payload: dict[str, object], *, timeout_seconds: float = 5.0) -> None:
            _ = (url, payload, timeout_seconds)
            attempts["count"] += 1
            if attempts["count"] < 2:
                from urllib.error import HTTPError

                raise HTTPError("http://example.test/hook", 503, "HTTP 503", hdrs=None, fp=None)

        with patch.dict(
            os.environ,
            {"AXON_WATCH_DELIVERY_WEBHOOK_URL": "http://127.0.0.1:9999/hook"},
            clear=False,
        ):
            with patch("app.delivery.adapters.webhook.post_json", side_effect=fake_post):
                result, error, reason = attempt_channel_delivery(
                    channel="webhook",
                    item={"title": "Alert", "summary": "Needs attention", "severity": "high"},
                    signal_id="signal_alert",
                )
        self.assertEqual("succeeded", result)
        self.assertEqual("", error)
        self.assertIn("retry_attempts=2", reason)
        self.assertEqual(2, attempts["count"])
