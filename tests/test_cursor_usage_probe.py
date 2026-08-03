from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.cli_runtime.cursor_usage_probe import (  # noqa: E402
    _read_cursor_auth_item,
    cursor_usage_allows_agent_retry,
    probe_cursor_usage,
)


class CursorUsageProbeTests(unittest.TestCase):
    def test_auth_probe_closes_its_read_only_state_database(self) -> None:
        connection = MagicMock()
        connection.execute.return_value.fetchone.return_value = ("token",)
        with (
            patch(
                "app.cli_runtime.cursor_usage_probe._state_db_path",
                return_value=Path("/tmp/cursor-state.vscdb"),
            ),
            patch(
                "app.cli_runtime.cursor_usage_probe.sqlite3.connect",
                return_value=connection,
            ),
        ):
            self.assertEqual("token", _read_cursor_auth_item("cursorAuth/accessToken"))
        connection.close.assert_called_once_with()

    def test_allows_retry_when_on_demand_or_auto_headroom(self) -> None:
        self.assertTrue(
            cursor_usage_allows_agent_retry(
                {
                    "ok": True,
                    "on_demand_enabled": True,
                    "auto_percent_used": 100,
                    "total_percent_used": 100,
                }
            )
        )
        self.assertTrue(
            cursor_usage_allows_agent_retry(
                {
                    "ok": True,
                    "on_demand_enabled": False,
                    "auto_percent_used": 87,
                    "total_percent_used": 90,
                }
            )
        )
        self.assertFalse(
            cursor_usage_allows_agent_retry(
                {
                    "ok": True,
                    "on_demand_enabled": False,
                    "auto_percent_used": 100,
                    "total_percent_used": 100,
                }
            )
        )
        self.assertTrue(cursor_usage_allows_agent_retry({"ok": False}))

    def test_probe_maps_period_usage_pools(self) -> None:
        with (
            patch(
                "app.cli_runtime.cursor_usage_probe._read_cursor_auth_item",
                side_effect=lambda key: {
                    "cursorAuth/accessToken": "tok",
                    "cursorAuth/stripeMembershipType": "pro",
                    "cursorAuth/stripeSubscriptionStatus": "active",
                }.get(key),
            ),
            patch(
                "app.cli_runtime.cursor_usage_probe._http_json",
                side_effect=lambda url, **kwargs: (
                    {
                        "membershipType": "pro",
                        "subscriptionStatus": "active",
                        "isOnBillableAuto": True,
                    }
                    if "full_stripe_profile" in url
                    else {
                        "planUsage": {
                            "autoPercentUsed": 86.9,
                            "apiPercentUsed": 100,
                            "totalPercentUsed": 89.5,
                        },
                        "displayMessage": "You've hit your usage limit",
                        "autoModelSelectedDisplayMessage": "Auto headroom",
                        "namedModelSelectedDisplayMessage": "API full",
                    }
                ),
            ),
            patch.dict("app.cli_runtime.cursor_usage_probe._USAGE_CACHE", {"fetched_at": 0.0, "payload": None}),
        ):
            usage = probe_cursor_usage(force_refresh=True)
        self.assertTrue(usage["ok"])
        self.assertEqual(86.9, usage["auto_percent_used"])
        self.assertEqual(100.0, usage["api_percent_used"])
        self.assertEqual(89.5, usage["total_percent_used"])
        self.assertTrue(usage["on_demand_enabled"])
        self.assertTrue(usage["allows_agent_retry"])


if __name__ == "__main__":
    unittest.main()
