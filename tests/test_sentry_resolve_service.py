from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

WATCH_SERVICE_ROOT = Path(__file__).resolve().parents[1] / "services" / "axon-watch"
for module_name in list(sys.modules):
    if module_name == "app" or module_name.startswith("app."):
        sys.modules.pop(module_name, None)
sys.path.insert(0, str(WATCH_SERVICE_ROOT))

from app.monitors import sentry_resolve_service  # noqa: E402


class SentryResolveServiceTests(unittest.TestCase):
    @patch("app.monitors.sentry_resolve_service.resolve_sentry_issue")
    @patch("app.monitors.sentry_resolve_service.merge_monitor_env", return_value={"SENTRY_AUTH_TOKEN": "t"})
    @patch("app.monitors.sentry_resolve_service._dashpro_project_root")
    @patch("app.monitors.dashpro_monitor.reset_monitor_probe_cache")
    def test_successful_resolve_resets_monitor_cache(
        self,
        reset_cache,
        project_root,
        _merge_env,
        resolve_issue,
    ) -> None:
        project_root.return_value = Path("/tmp")
        resolve_issue.return_value = {"ok": True, "issue_id": "1", "status": "resolved"}
        result = sentry_resolve_service.resolve_watch_sentry_issue("1")
        self.assertTrue(result["ok"])
        reset_cache.assert_called_once_with()

    @patch("app.monitors.sentry_resolve_service.resolve_sentry_issue")
    @patch("app.monitors.sentry_resolve_service.merge_monitor_env", return_value={"SENTRY_AUTH_TOKEN": "t"})
    @patch("app.monitors.sentry_resolve_service._dashpro_project_root")
    @patch("app.monitors.dashpro_monitor.reset_monitor_probe_cache")
    def test_failed_resolve_does_not_reset_cache(
        self,
        reset_cache,
        project_root,
        _merge_env,
        resolve_issue,
    ) -> None:
        project_root.return_value = Path("/tmp")
        resolve_issue.return_value = {"ok": False, "reason": "missing_write_scope"}
        result = sentry_resolve_service.resolve_watch_sentry_issue("1")
        self.assertFalse(result["ok"])
        reset_cache.assert_not_called()


if __name__ == "__main__":
    unittest.main()
