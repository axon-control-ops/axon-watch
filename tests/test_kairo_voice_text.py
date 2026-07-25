from __future__ import annotations

import sys
import unittest
from pathlib import Path

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.kairo_voice_text import normalize_spoken_line  # noqa: E402


class KairoVoiceTextTests(unittest.TestCase):
    def test_softens_paths_and_emoji_for_speech(self) -> None:
        spoken = normalize_spoken_line("Open apps/console-web/src/lib/foo.ts:42 🙂")
        self.assertNotIn("/", spoken)
        self.assertNotIn(":", spoken)
        self.assertNotIn("🙂", spoken)
        self.assertIn("apps", spoken.lower())
        self.assertIn("42", spoken)

    def test_keeps_clock_times(self) -> None:
        spoken = normalize_spoken_line("Briefing ready at 12:30.")
        self.assertIn("12:30", spoken)

    def test_strips_literal_symbol_words(self) -> None:
        spoken = normalize_spoken_line(
            "Open apps slash console web colon forty two with a smiley face"
        )
        self.assertNotIn("slash", spoken.lower())
        self.assertNotIn("colon", spoken.lower())
        self.assertNotIn("smiley", spoken.lower())
        self.assertIn("apps", spoken.lower())

    def test_never_addresses_listener_as_operator(self) -> None:
        spoken = normalize_spoken_line("Hello operator, systems are nominal.")
        self.assertNotIn("operator", spoken.lower())
        self.assertIn("systems are nominal", spoken.lower())

        rewritten = normalize_spoken_line("Smoke run is ready for operator review.")
        self.assertIn("for your review", rewritten.lower())
        self.assertNotIn("operator", rewritten.lower())


if __name__ == "__main__":
    unittest.main()
