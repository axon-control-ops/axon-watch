import http.client
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

CONTROL_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_ROOT))

from app.azure_tts import (  # noqa: E402
    CONTINUATION_LEADING_AUDIO_GUARD_MS,
    LEADING_AUDIO_GUARD_MS,
    SOFT_ONSET_LEADING_AUDIO_GUARD_MS,
    TTS_READ_ATTEMPTS,
    TTS_REQUEST_TIMEOUT_SECONDS,
    TTS_RETRY_BACKOFF_SECONDS,
    azure_speech_configured,
    build_azure_ssml,
    extract_azure_speech_key,
    leading_audio_guard_ms,
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

    def test_adds_extra_lead_in_for_soft_agent_ack_openings(self) -> None:
        self.assertEqual(
            leading_audio_guard_ms("Walking that now, Sir King."),
            SOFT_ONSET_LEADING_AUDIO_GUARD_MS,
        )
        self.assertEqual(
            leading_audio_guard_ms("Working that now, Sir King."),
            SOFT_ONSET_LEADING_AUDIO_GUARD_MS,
        )
        self.assertEqual(
            leading_audio_guard_ms("Done, Sir King."),
            LEADING_AUDIO_GUARD_MS,
        )
        soft_ssml = build_azure_ssml("Walking that now, Sir King.")
        self.assertIn(
            f"<mstts:silence type='Leading' value='{SOFT_ONSET_LEADING_AUDIO_GUARD_MS}ms'/>",
            soft_ssml,
        )
        self.assertIn("xmlns:mstts='https://www.w3.org/2001/mstts'", soft_ssml)

    def test_continuation_chunks_skip_long_lead_in(self) -> None:
        self.assertEqual(
            leading_audio_guard_ms("Next sentence continues.", continuation=True),
            CONTINUATION_LEADING_AUDIO_GUARD_MS,
        )
        ssml = build_azure_ssml("Next sentence continues.", continuation=True)
        self.assertIn(
            f"<mstts:silence type='Leading' value='{CONTINUATION_LEADING_AUDIO_GUARD_MS}ms'/>",
            ssml,
        )
        self.assertNotIn("<break time='120ms'/>", ssml)
        self.assertNotIn("<break time='200ms'/>", ssml)

    def test_relative_rate_and_pitch_attrs(self) -> None:
        self.assertEqual(azure_voice_rate_attr(0.85), "-15%")
        self.assertEqual(azure_voice_rate_attr(1.05), "+5%")
        self.assertEqual(azure_voice_pitch_attr(1.04), "+4%")
        calm = build_azure_ssml("Hello operator", rate=0.85, pitch=1.04)
        self.assertIn("rate='-15%'", calm)
        self.assertIn("pitch='+4%'", calm)
        self.assertIn(
            f"<mstts:silence type='Leading' value='{LEADING_AUDIO_GUARD_MS}ms'/>",
            calm,
        )

    def test_returns_none_when_azure_is_not_configured(self) -> None:
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("AZURE_SPEECH_KEY", None)
            os.environ.pop("AZURE_SPEECH_REGION", None)
            with patch("app.cli_runtime.vault_keys.runtime_vault_env", return_value={}):
                self.assertFalse(azure_speech_configured())
                self.assertIsNone(synthesize_azure_speech("Hello"))

    def test_retry_budget_stays_below_browser_timeout(self) -> None:
        total_budget = (
            TTS_READ_ATTEMPTS * TTS_REQUEST_TIMEOUT_SECONDS
            + TTS_RETRY_BACKOFF_SECONDS * (TTS_READ_ATTEMPTS - 1)
        )
        self.assertLess(total_budget, 15)

    def test_incomplete_read_retries_only_within_budget(self) -> None:
        with (
            patch(
                "app.azure_tts.resolve_azure_speech_credentials",
                return_value=("", "southafricanorth"),
            ),
            patch(
                "app.azure_tts.urllib.request.urlopen",
                side_effect=http.client.IncompleteRead(b"partial"),
            ) as mock_open,
            patch("app.azure_tts.time.sleep") as mock_sleep,
        ):
            result = synthesize_azure_speech(
                "Hello operator",
                key="abc1234567890123456789012345678",
            )
        self.assertIsNone(result)
        self.assertEqual(mock_open.call_count, TTS_READ_ATTEMPTS)
        mock_sleep.assert_called_once_with(TTS_RETRY_BACKOFF_SECONDS)

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
