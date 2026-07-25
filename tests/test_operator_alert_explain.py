"""Golden parity tests for plain-English operator alert explainers."""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.operator_alert_explain import explain_operator_alert  # noqa: E402
from app.spoken_alert_policy import resolve_spoken_alert  # noqa: E402

GOLDENS_PATH = (
    Path(__file__).resolve().parents[1] / "config" / "operator-alert-explain-goldens.json"
)


class OperatorAlertExplainGoldenTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.goldens = json.loads(GOLDENS_PATH.read_text(encoding="utf-8"))

    def test_goldens_match_python_explainer(self) -> None:
        for case in self.goldens:
            with self.subTest(case["id"]):
                raw = case["input"]
                explained = explain_operator_alert(
                    signal_id=str(raw.get("signal_id") or ""),
                    title=str(raw.get("title") or ""),
                    summary=str(raw.get("summary") or ""),
                    meta=raw.get("meta") if isinstance(raw.get("meta"), dict) else None,
                    pending_approvals=int(raw.get("pending_approvals") or 0),
                    reason=str(raw.get("reason") or ""),
                )
                for needle in case["expect_spoken_contains"]:
                    self.assertIn(needle.lower(), explained["spoken"].lower())
                for needle in case["expect_what_contains"]:
                    self.assertIn(needle.lower(), explained["what"].lower())
                for needle in case["expect_agent_do_contains"]:
                    self.assertIn(needle.lower(), explained["agent_do"].lower())

    def test_eligible_spoken_alert_includes_explanation(self) -> None:
        payload = resolve_spoken_alert(
            settings={
                "operator_persona_enabled": True,
                "spoken_alerts_enabled": True,
                "privacy_mode": False,
            },
            pending_approvals=1,
            top_signal=None,
        )
        self.assertTrue(payload["eligible"])
        explained = payload["explanation"]
        assert isinstance(explained, dict)
        for key in ("what", "you_do", "agent_do", "spoken"):
            self.assertTrue(str(explained.get(key) or "").strip())


if __name__ == "__main__":
    unittest.main()
