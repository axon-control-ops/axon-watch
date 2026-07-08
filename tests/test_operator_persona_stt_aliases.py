"""Tests for VAXON STT alias normalization."""

from __future__ import annotations

import unittest

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
        ):
            normalized = normalize_persona_stt_aliases(phrase)
            self.assertIn(OPERATOR_PERSONA_NAME, normalized)

    def test_leaves_unrelated_words(self) -> None:
        self.assertEqual(
            normalize_persona_stt_aliases("vision check health"),
            "vision check health",
        )


if __name__ == "__main__":
    unittest.main()
