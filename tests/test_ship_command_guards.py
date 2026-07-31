from __future__ import annotations

import sys
import unittest
from pathlib import Path

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.terminal.ship_command_guards import (  # noqa: E402
    ShipCommandGuardError,
    assert_ship_command_allowed,
)


class ShipCommandGuardsTests(unittest.TestCase):
    def test_allows_dashpro_canary_from_dashpro(self) -> None:
        assert_ship_command_allowed(
            workspace_id="workspace_dashpro",
            command="npm run ota:canary",
            source_workspace_id="workspace_dashpro",
        )

    def test_rejects_ota_from_young_eagles_workspace(self) -> None:
        with self.assertRaisesRegex(ShipCommandGuardError, "workspace_dashpro"):
            assert_ship_command_allowed(
                workspace_id="workspace_young_eagles_day_care",
                command="npm run ota:production",
            )

    def test_rejects_ye_retarget_to_dashpro(self) -> None:
        with self.assertRaisesRegex(ShipCommandGuardError, "caller workspace"):
            assert_ship_command_allowed(
                workspace_id="workspace_dashpro",
                command=(
                    "bash -lc 'cd /home/edp/Projectx/product/dashpro && "
                    "RELEASE_GUARD_ALLOW_PRODUCTION_OTA=1 npm run ota:production'"
                ),
                source_workspace_id="workspace_young_eagles_day_care",
            )

    def test_rejects_cd_dashpro_ota_from_client_ops(self) -> None:
        with self.assertRaises(ShipCommandGuardError):
            assert_ship_command_allowed(
                workspace_id="workspace_young_eagles_day_care",
                command="cd /home/edp/Projectx/product/dashpro && npm run ota:canary",
            )

    def test_allows_non_ship_commands_anywhere(self) -> None:
        assert_ship_command_allowed(
            workspace_id="workspace_young_eagles_day_care",
            command="echo hello",
            source_workspace_id="workspace_young_eagles_day_care",
        )
