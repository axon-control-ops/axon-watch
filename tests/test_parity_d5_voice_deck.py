"""P-D5 Vue voice deck parity tests."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


class ParityD5VoiceDeckTests(unittest.TestCase):
    def test_default_verify_wiring_includes_parity_d5_tests(self) -> None:
        package = json.loads((REPO_ROOT / "package.json").read_text(encoding="utf-8"))
        verify_script = package["scripts"]["verify:contracts"]
        self.assertIn("tests.test_parity_d5_voice_deck", verify_script)

    def test_voice_deck_module_and_app_boot_wiring_present(self) -> None:
        voice_deck = REPO_ROOT / "apps/console-web/src/features/voice-deck/voice-deck.ts"
        use_voice_deck = REPO_ROOT / "apps/console-web/src/features/voice-deck/use-voice-deck.ts"
        app_vue = REPO_ROOT / "apps/console-web/src/App.vue"
        self.assertTrue(voice_deck.is_file())
        self.assertTrue(use_voice_deck.is_file())
        app_text = app_vue.read_text(encoding="utf-8")
        self.assertIn("useVoiceDeckOnBoot", app_text)
        deck_text = voice_deck.read_text(encoding="utf-8")
        self.assertIn("registerVoiceDeckSpokenAlertHandler", deck_text)
        self.assertIn("registerVoiceDeckOnBoot", deck_text)


if __name__ == "__main__":
    unittest.main()
