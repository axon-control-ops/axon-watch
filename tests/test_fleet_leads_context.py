from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.workspace_agents.config_loader import CompanyConfig, EmployeeConfig  # noqa: E402
from app.workspace_agents.fleet_leads_context import (  # noqa: E402
    FLEET_LEADS_MARKER,
    _project_kind,
    build_fleet_leads_context,
    format_fleet_leads_block,
)


class FleetLeadsContextTests(unittest.TestCase):
    def test_format_includes_dashpro_and_young_eagles_owns(self) -> None:
        block = format_fleet_leads_block(
            [
                {
                    "workspace_id": "workspace_dashpro",
                    "company_name": "DashPro",
                    "lead_name": "Dana",
                    "owns": "Expo app UI and OTA",
                    "display_name": "DashPro",
                    "project_kind": "product app",
                },
                {
                    "workspace_id": "workspace_young_eagles_day_care",
                    "company_name": "Young Eagles Day Care",
                    "lead_name": "Imani",
                    "owns": "Centre ops; hand off app UI to DashPro",
                    "display_name": "Young Eagles Day Care",
                    "project_kind": "client ops",
                },
            ]
        )
        self.assertIn(FLEET_LEADS_MARKER, block)
        self.assertIn("Dana", block)
        self.assertIn("workspace_dashpro", block)
        self.assertIn("Imani", block)
        self.assertIn("workspace_young_eagles_day_care", block)
        self.assertIn("POST /api/workspaces/{source}/handoffs", block)
        self.assertIn("workspace_axon_watch", block)
        self.assertIn("EAS Update only ships JS/assets", block)

    def test_project_kind_uses_axon_watch_not_invented_axon_x_id(self) -> None:
        self.assertEqual(
            "Axon console",
            _project_kind(
                workspace_id="workspace_axon_watch",
                project_root="/home/edp/axon-nvme/repos/axon-watch",
                display_name="axon-watch",
                company_name="Axon-X",
            ),
        )
        self.assertNotEqual(
            "Axon console",
            _project_kind(
                workspace_id="workspace_other",
                project_root="/tmp/other",
                display_name="other",
                company_name="Other",
            ),
        )

    def test_build_uses_binding_labels_even_when_roots_missing(self) -> None:
        companies = {
            "workspace_dashpro": CompanyConfig(
                company_name="DashPro",
                employees=(
                    EmployeeConfig(
                        name="Dana",
                        role="lead",
                        owns="DashPro app UI and OTA",
                        enabled=True,
                        primary=True,
                    ),
                ),
            ),
            "workspace_young_eagles_day_care": CompanyConfig(
                company_name="Young Eagles Day Care",
                employees=(
                    EmployeeConfig(
                        name="Imani",
                        role="lead",
                        owns="Centre ops; hand off app UI to DashPro",
                        enabled=True,
                        primary=True,
                    ),
                ),
            ),
            "workspace_axon_watch": CompanyConfig(
                company_name="Axon-X",
                employees=(
                    EmployeeConfig(
                        name="Mira",
                        role="lead",
                        owns="Axon console",
                        enabled=True,
                        primary=True,
                    ),
                ),
            ),
        }
        with tempfile.TemporaryDirectory() as tmp:
            bindings_path = Path(tmp) / "bindings.json"
            bindings_path.write_text(
                json.dumps(
                    {
                        "bindings": {
                            "workspace_dashpro": {
                                "display_name": "DashPro",
                                "project_root": "/definitely/missing/product/dashpro",
                            },
                            "workspace_young_eagles_day_care": {
                                "display_name": "Young Eagles Day Care",
                                "project_root": "/definitely/missing/client/young-eagles",
                            },
                            "workspace_axon_watch": {
                                "display_name": "axon-watch",
                                "project_root": "/definitely/missing/repos/axon-watch",
                            },
                        }
                    }
                ),
                encoding="utf-8",
            )
            with patch(
                "app.workspace_agents.config_loader.load_workspace_agent_configs",
                return_value=({}, {}, companies, []),
            ), patch(
                "app.workspace_project_bindings.default_bindings_file",
                return_value=bindings_path,
            ):
                block = build_fleet_leads_context()

        self.assertIn(FLEET_LEADS_MARKER, block)
        self.assertIn("Dana", block)
        self.assertIn("Imani", block)
        self.assertIn("Mira", block)
        self.assertIn("product app", block)
        self.assertIn("client ops", block)
        self.assertIn("Axon console", block)
