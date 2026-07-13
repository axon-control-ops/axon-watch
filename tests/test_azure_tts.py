import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

CONTROL_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_ROOT))

from app.azure_tts import (  # noqa: E402
    LEADING_AUDIO_GUARD_MS,
    azure_speech_configured,
    build_azure_ssml,
    extract_azure_speech_key,
    resolve_azure_speech_credentials,
    synthesize_azure_speech,
)
from app.voice_tuning import azure_voice_pitch_attr, azure_voice_rate_attr  # noqa: E402


class AzureTtsTests(unittest.TestCase):
    def test_detects_configured_keys_and_builds_ssml(self) -> None:
        self.assertEqual(extract_azure_speech_key("changeme"), "")
        self.assertEqual(
            extract_azure_speech_key("abc1234567890123456789012345678"),
            "abc1234567890123456789012345678",
        )
        ssml = build_azure_ssml("Hello operator")
        self.assertIn("Hello operator", ssml)
        self.assertIn("en-GB-RyanNeural", ssml)
        # axon-local parity: relative prosody, no chat express-as.
        self.assertIn("prosody", ssml)
        self.assertIn("rate='+0%'", ssml)
        self.assertIn("pitch=", ssml)
        self.assertNotIn("express-as", ssml)
        self.assertNotIn("style='chat'", ssml)

    def test_relative_rate_and_pitch_attrs(self) -> None:
        self.assertEqual(azure_voice_rate_attr(0.85), "-15%")
        self.assertEqual(azure_voice_rate_attr(1.05), "+5%")
        self.assertEqual(azure_voice_pitch_attr(1.04), "+4%")
        calm = build_azure_ssml("Hello operator", rate=0.85, pitch=1.04)
        self.assertIn("rate='-15%'", calm)
        self.assertIn("pitch='+4%'", calm)
        self.assertIn(f"<break time='{LEADING_AUDIO_GUARD_MS}ms'/>", calm)

    def test_returns_none_when_azure_is_not_configured(self) -> None:
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("AZURE_SPEECH_KEY", None)
            os.environ.pop("AZURE_SPEECH_REGION", None)
            with patch("app.cli_runtime.vault_keys.runtime_vault_env", return_value={}):
                self.assertFalse(azure_speech_configured())
                self.assertIsNone(synthesize_azure_speech("Hello"))

    @patch("app.cli_runtime.vault_keys.runtime_vault_env")
    def test_resolve_azure_speech_credentials_from_unlocked_vault(self, mock_runtime_env) -> None:
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("AZURE_SPEECH_KEY", None)
            os.environ.pop("AZURE_SPEECH_REGION", None)
            mock_runtime_env.return_value = {
                "azure_speech_key": "abc1234567890123456789012345678",
                "azure_speech_region": "southafricanorth",
            }

            key, region = resolve_azure_speech_credentials()
            self.assertEqual(key, "abc1234567890123456789012345678")
            self.assertEqual(region, "southafricanorth")
            self.assertTrue(azure_speech_configured())


if __name__ == "__main__":
    unittest.main()
