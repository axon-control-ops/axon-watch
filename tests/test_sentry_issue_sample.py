"""Tests for Sentry issue sample extraction."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

WATCH_SERVICE_ROOT = Path(__file__).resolve().parents[1] / "services" / "axon-watch"
for module_name in list(sys.modules):
    if module_name == "app" or module_name.startswith("app."):
        sys.modules.pop(module_name, None)
sys.path.insert(0, str(WATCH_SERVICE_ROOT))

from app.monitors.sentry_issue_sample import extract_sentry_issue_sample  # noqa: E402


class SentryIssueSampleTests(unittest.TestCase):
    def test_extracts_bounded_issue_fields(self) -> None:
        sample = extract_sentry_issue_sample(
            [
                {
                    "id": "99",
                    "shortId": "RN-99",
                    "title": "Boom",
                    "level": "error",
                    "count": "3",
                    "permalink": "https://sentry.io/issues/99/",
                    "culprit": "main.ts",
                },
                {"id": ""},
                "skip-me",
            ],
            limit=1,
        )
        self.assertEqual(1, len(sample))
        self.assertEqual("99", sample[0]["id"])
        self.assertEqual("RN-99", sample[0]["short_id"])
        self.assertEqual(3, sample[0]["count"])


if __name__ == "__main__":
    unittest.main()
