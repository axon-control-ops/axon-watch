"""Tests for VAXON STT alias normalization."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.operator_persona_name import OPERATOR_PERSONA_NAME
from app.operator_persona_stt_aliases import normalize_persona_stt_aliases


class OperatorPersonaSttAliasesTests(unittest.TestCase):
    def test_maps_common_mishears(self) -> None:
        for phrase in (
            "hey vixen check health",
            "hey vicksen check health",
            "hey vikson check health",
            "hey backs on check health",
            "hey wax on check health",
            "hey axon vixen check health",
            "hey vaccine check health",
            "hey excent check health",
        ):
            normalized = normalize_persona_stt_aliases(phrase)
            self.assertIn(OPERATOR_PERSONA_NAME, normalized)

    def test_normalizes_common_dashpro_workspace_mishears(self) -> None:
        self.assertIn(
            "DashPro workspace",
            normalize_persona_stt_aliases("check what the best pro workspace justick"),
        )
        self.assertIn(
            "DashPro workspace",
            normalize_persona_stt_aliases("pull up those probox space and check what is doing"),
        )

    def test_leaves_unrelated_words(self) -> None:
        self.assertEqual(
            normalize_persona_stt_aliases("vision check health"),
            "vision check health",
        )


if __name__ == "__main__":
    unittest.main()
