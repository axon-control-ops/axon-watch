from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.kairo_lead_charter_intents import (  # noqa: E402
    is_lead_charter_utterance,
    maybe_handle_lead_charter_intent,
    resolve_lead_charter_workspace_id,
)


class LeadCharterIntentTests(unittest.TestCase):
    def test_detects_charter_utterance(self) -> None:
        text = (
            "Charter Lindi to stand up EDP Excellence Aftercare as a sibling app "
            "with shared DashPro DNA, own repo/deploy (Vercel), Grade 1-7 focus."
        )
        self.assertTrue(is_lead_charter_utterance(text))
        self.assertEqual(
            "workspace_edudashpro_school",
            resolve_lead_charter_workspace_id(text, workspace_id=None),
        )

    def test_persists_lead_plan_for_school_workspace(self) -> None:
        text = (
            "Charter Lindi to stand up EDP Excellence Aftercare as a sibling app "
            "with shared DashPro DNA, own repo/deploy (Vercel), Grade 1-7 focus. "
            "Do not hard fork the whole DashPro tree or touch DashPro prod."
        )
        with patch(
            "app.kairo_lead_charter_intents.persist_charter_lead_plan",
            return_value={
                "plan_id": "plan_test_edp",
                "workspace_id": "workspace_edudashpro_school",
                "plan": {
                    "goal": text,
                    "mode": "auto",
                    "items": [
                        {"owner_role": "frontend"},
                        {"owner_role": "backend"},
                        {"owner_role": "integrations"},
                        {"owner_role": "watcher"},
                    ],
                },
            },
        ) as persist:
            payload = maybe_handle_lead_charter_intent(
                content=text,
                workspace_id="workspace_edudashpro_school",
                guest_name=None,
            )
        self.assertIsNotNone(payload)
        assert payload is not None
        persist.assert_called_once()
        self.assertIn("plan_test_edp", str(payload["reply"]))
        self.assertEqual(
            {
                "type": "switch_workspace",
                "workspace_id": "workspace_edudashpro_school",
            },
            payload["action"],
        )


if __name__ == "__main__":
    unittest.main()
