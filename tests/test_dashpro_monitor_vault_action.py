from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

WATCH_ROOT = Path(__file__).resolve().parents[1] / "services" / "axon-watch"
sys.path.insert(0, str(WATCH_ROOT))

from app.monitors.dashpro_monitor import probe_dashpro_monitor_records  # noqa: E402


class DashproMonitorVaultActionTests(unittest.TestCase):
    @patch("app.monitors.monitor_probe.check_sentry_recent_issues", return_value=("skipped", "missing token"))
    def test_skipped_monitor_records_include_vault_action(self, _check) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_root = Path(tmp)
            config = {
                "enabled": True,
                "workspace_id": "workspace_dashpro",
                "project_root": str(project_root),
                "checks": [{"id": "sentry", "type": "sentry_recent_issues", "service": "sentry"}],
            }
            with patch("app.monitors.dashpro_monitor.load_monitor_config", return_value=config):
                records = probe_dashpro_monitor_records()
        self.assertEqual(1, len(records))
        self.assertEqual("skipped", records[0]["status"])
        self.assertEqual("/vault", records[0]["vault_action"]["surface"])


if __name__ == "__main__":
    unittest.main()
