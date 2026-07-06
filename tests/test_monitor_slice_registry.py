from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

WATCH_ROOT = Path(__file__).resolve().parents[1] / "services" / "axon-watch"
sys.path.insert(0, str(WATCH_ROOT))

from app.monitors.monitor_probe import probe_all_monitor_slices  # noqa: E402
from app.monitors.slice_registry import list_monitor_slice_paths, load_monitor_slices  # noqa: E402


class MonitorSliceRegistryTests(unittest.TestCase):
    def test_list_monitor_slice_paths_finds_dashpro_config(self) -> None:
        paths = list_monitor_slice_paths(WATCH_ROOT.parents[1] / "config")
        names = [path.name for path in paths]
        self.assertIn("dashpro-monitor-slice.json", names)

    def test_probe_all_monitor_slices_runs_each_enabled_slice(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config_dir = Path(tmp)
            project_root = config_dir / "project"
            project_root.mkdir()
            (config_dir / "alpha-monitor-slice.json").write_text(
                json.dumps(
                    {
                        "enabled": True,
                        "workspace_id": "workspace_alpha",
                        "workspace_label": "Alpha",
                        "project_root": str(project_root),
                        "checks": [
                            {
                                "id": "alpha_sentry",
                                "type": "sentry_recent_issues",
                                "service": "Sentry",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            with patch(
                "app.monitors.monitor_probe.check_sentry_recent_issues",
                return_value=("ok", "fine"),
            ):
                records = probe_all_monitor_slices(config_dir)
        self.assertEqual(1, len(records))
        self.assertEqual("workspace_alpha", records[0]["workspace_id"])
        self.assertEqual("Alpha", records[0]["workspace_label"])

    def test_load_monitor_slices_ignores_missing_dir(self) -> None:
        self.assertEqual([], load_monitor_slices(Path("/tmp/does-not-exist-monitor-slices")))


if __name__ == "__main__":
    unittest.main()
