"""Workspace company parity — named companies + diversified template staffing."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.workspace_agents import build_company_roster, load_workspace_agent_configs  # noqa: E402
from app.workspace_agents.catalog import stable_role_persona  # noqa: E402


class WorkspaceCompanyParityTests(unittest.TestCase):
    def test_tps_named_company_is_not_axon_x_clone(self) -> None:
        configs, defaults, companies, staffing = load_workspace_agent_configs()
        roster = build_company_roster(
            "workspace_tps",
            configs=configs,
            defaults=defaults,
            companies=companies,
            staffing_template=staffing,
        )
        names = [str(row["name"]) for row in roster["employees"]]  # type: ignore[index]
        self.assertEqual(["Noor", "Blair", "Vera", "Hugo", "Tess"], names)
        self.assertTrue(all(row.get("azure_voice_id") for row in roster["employees"]))  # type: ignore[index]

    def test_template_staffing_is_stable_per_workspace(self) -> None:
        first, _ = stable_role_persona("workspace_audio_transcribe", "lead")
        second, voice = stable_role_persona("workspace_audio_transcribe", "lead")
        other, _ = stable_role_persona("workspace_web", "lead")
        self.assertEqual(first, second)
        self.assertTrue(voice)
        # Different workspaces may share a bank slot, but personas are deterministic.
        self.assertTrue(first)
        self.assertTrue(other)

    def test_unconfigured_bound_workspace_gets_voices(self) -> None:
        roster = build_company_roster(
            "workspace_audio_transcribe",
            record={
                "workspace_id": "workspace_audio_transcribe",
                "display_name": "audio-transcribe",
                "connection_kind": "project_path",
            },
            configs={},
            defaults={
                "role": "lead",
                "company_name_template": "{display_name}",
            },
            companies={},
            staffing_template=[
                {"role": "lead", "schedule": "on_demand"},
                {"role": "watcher", "schedule": "always_on"},
                {"role": "frontend", "schedule": "continuous"},
                {"role": "backend", "schedule": "continuous"},
                {"role": "integrations", "schedule": "continuous"},
            ],
        )
        self.assertEqual(5, roster["employee_count"])
        axon_clone = {"Mira", "Rowan", "Jules", "Reed", "Quinn"}
        names = {str(row["name"]) for row in roster["employees"]}  # type: ignore[index]
        # Must not be the exact Axon-X five for every unconfigured workspace.
        self.assertNotEqual(names, axon_clone)
        self.assertTrue(all(row.get("azure_voice_id") for row in roster["employees"]))  # type: ignore[index]

    def test_pending_operator_decision_keeps_lead_out_of_idle(self) -> None:
        with patch(
            "app.workspace_agents._pending_decision_for_role",
            side_effect=lambda _workspace, role: (
                {"receipt_id": "ask-1", "title": "Dana needs a decision"}
                if role == "lead" else None
            ),
        ):
            roster = build_company_roster(
                "workspace_demo_decision",
                record={"workspace_id": "workspace_demo_decision", "display_name": "Demo"},
                configs={},
                defaults={"role": "lead", "company_name_template": "{display_name}"},
                companies={},
                staffing_template=[{"role": "lead", "schedule": "on_demand"}],
            )
        lead = roster["employees"][0]  # type: ignore[index]
        self.assertEqual("waiting_approval", lead["status"])
        self.assertEqual("ask-1", lead["pending_decision_id"])


if __name__ == "__main__":
    unittest.main()
