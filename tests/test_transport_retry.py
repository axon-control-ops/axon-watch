"""Tests for monitor transport retry helpers."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from urllib.error import URLError

WATCH_SERVICE_ROOT = Path(__file__).resolve().parents[1] / "services" / "axon-watch"
sys.path.insert(0, str(WATCH_SERVICE_ROOT))

from app.monitors.transport_retry import is_transient_transport_error  # noqa: E402


class TransportRetryTests(unittest.TestCase):
    def test_detects_dns_resolution_failure(self) -> None:
        exc = OSError("[Errno -3] Temporary failure in name resolution")
        self.assertTrue(is_transient_transport_error(exc))

    def test_detects_nested_urlerror(self) -> None:
        exc = URLError(OSError("[Errno -3] Temporary failure in name resolution"))
        self.assertTrue(is_transient_transport_error(exc))


if __name__ == "__main__":
    unittest.main()
