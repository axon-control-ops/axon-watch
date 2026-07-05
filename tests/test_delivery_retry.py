"""Unit tests for delivery retry behavior."""

from __future__ import annotations

import unittest

from tests.support.watch_app_loader import load_watch_app, restore_app_modules


class DeliveryRetryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._watch_app, cls._watch_modules = load_watch_app()
        from app.delivery import retry as delivery_retry  # noqa: WPS433

        cls._delivery_retry = delivery_retry

    @classmethod
    def tearDownClass(cls) -> None:
        restore_app_modules(cls._watch_modules)

    def test_retryable_errors_include_transient_http_codes(self) -> None:
        self.assertTrue(self._delivery_retry.is_retryable_error("HTTP 503"))
        self.assertTrue(self._delivery_retry.is_retryable_error("connection refused"))
        self.assertFalse(self._delivery_retry.is_retryable_error("HTTP 401"))

    def test_deliver_with_retry_recovers_after_transient_failure(self) -> None:
        attempts = {"count": 0}

        def deliver() -> tuple[str, str, str]:
            attempts["count"] += 1
            if attempts["count"] < 3:
                return ("failed", "HTTP 503", "webhook_http_error")
            return ("succeeded", "", "webhook_delivered")

        result, error, reason = self._delivery_retry.deliver_with_retry(deliver, max_attempts=3)
        self.assertEqual("succeeded", result)
        self.assertEqual("", error)
        self.assertIn("retry_attempts=3", reason)
        self.assertEqual(3, attempts["count"])

    def test_non_retryable_error_stops_immediately(self) -> None:
        attempts = {"count": 0}

        def deliver() -> tuple[str, str, str]:
            attempts["count"] += 1
            return ("failed", "HTTP 401", "webhook_http_error")

        result, _, _ = self._delivery_retry.deliver_with_retry(deliver, max_attempts=3)
        self.assertEqual("failed", result)
        self.assertEqual(1, attempts["count"])


if __name__ == "__main__":
    unittest.main()
