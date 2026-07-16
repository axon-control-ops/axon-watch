from __future__ import annotations

import io
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from tests.support.control_plane_db import isolate_control_plane_db

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.azure_stt import (  # noqa: E402
    MAX_STT_UPLOAD_BYTES,
    azure_stt_configured,
    resolve_stt_language,
    stt_availability_payload,
    transcribe_azure_stt,
)
from app.main import app  # noqa: E402
from app.persistence import operator_presence_settings_store, run_store  # noqa: E402


class AzureSttModuleTests(unittest.TestCase):
    def test_resolve_stt_language_defaults_and_validates(self) -> None:
        self.assertEqual(resolve_stt_language(""), "en-US")
        self.assertEqual(resolve_stt_language("en-GB"), "en-GB")
        self.assertEqual(resolve_stt_language("bad locale"), "en-US")

    def test_rejects_oversize_and_unsupported_formats(self) -> None:
        with self.assertRaises(ValueError):
            transcribe_azure_stt(b"x" * (MAX_STT_UPLOAD_BYTES + 1))
        with self.assertRaises(ValueError):
            transcribe_azure_stt(b"abc", filename="capture.webm", mime_type="audio/webm")

    @patch("app.azure_stt.resolve_azure_speech_credentials", return_value=("", "southafricanorth"))
    def test_returns_none_when_azure_not_configured(self, _mock_creds) -> None:
        self.assertFalse(azure_stt_configured())
        self.assertIsNone(
            transcribe_azure_stt(b"abc", filename="capture.ogg", mime_type="audio/ogg"),
        )

    @patch("app.azure_stt.urllib.request.urlopen")
    @patch(
        "app.azure_stt.resolve_azure_speech_credentials",
        return_value=("abc1234567890123456789012345678", "southafricanorth"),
    )
    def test_parses_success_payload_with_confidence(self, _mock_creds, mock_urlopen) -> None:
        payload = (
            b'{"RecognitionStatus":"Success","NBest":[{"Confidence":0.91,'
            b'"Display":"Vaxon briefing status"}]}'
        )
        mock_urlopen.return_value.__enter__.return_value.read.return_value = payload
        result = transcribe_azure_stt(
            b"audio",
            filename="capture.ogg",
            mime_type="audio/ogg",
            language="en-US",
        )
        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(result.transcript, "VAXON briefing status")
        self.assertAlmostEqual(result.confidence or 0.0, 0.91)

    def test_availability_payload_reports_limits(self) -> None:
        payload = stt_availability_payload()
        self.assertIn("available", payload)
        self.assertEqual(payload.get("max_upload_bytes"), MAX_STT_UPLOAD_BYTES)
        self.assertEqual(payload.get("supported_mime_types"), ["audio/ogg", "audio/wav"])
        self.assertEqual(payload.get("browser_fallback_mime_types"), ["audio/webm"])


class KairoSttRouteTests(unittest.TestCase):
    def setUp(self) -> None:
        isolate_control_plane_db(self, run_store)
        self.client = TestClient(app)

    def test_get_stt_probe_returns_contract(self) -> None:
        response = self.client.get("/api/kairo/stt")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn("available", payload)
        self.assertIn("provider", payload)
        self.assertIn("max_upload_bytes", payload)

    def test_post_stt_blocks_privacy_mode(self) -> None:
        operator_presence_settings_store.save_settings(
            {
                **operator_presence_settings_store.load_settings(),
                "privacy_mode": True,
            }
        )
        response = self.client.post(
            "/api/kairo/stt",
            files={"file": ("capture.ogg", io.BytesIO(b"abc"), "audio/ogg")},
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertFalse(payload["available"])
        self.assertEqual(payload["reason"], "privacy_mode")
        self.assertEqual(payload["provider"], "browser")

    def test_post_stt_rejects_empty_payload(self) -> None:
        operator_presence_settings_store.save_settings(
            {
                **operator_presence_settings_store.load_settings(),
                "privacy_mode": False,
            }
        )
        response = self.client.post(
            "/api/kairo/stt",
            files={"file": ("capture.ogg", io.BytesIO(b""), "audio/ogg")},
        )
        self.assertEqual(response.status_code, 400)

    @patch("app.azure_stt.transcribe_azure_stt")
    def test_post_stt_returns_transcript_contract(self, mock_transcribe) -> None:
        from app.azure_stt import AzureSttResult

        operator_presence_settings_store.save_settings(
            {
                **operator_presence_settings_store.load_settings(),
                "privacy_mode": False,
            }
        )
        mock_transcribe.return_value = AzureSttResult(
            transcript="check tunnel status",
            confidence=0.88,
        )
        response = self.client.post(
            "/api/kairo/stt",
            files={"file": ("capture.ogg", io.BytesIO(b"audio"), "audio/ogg")},
            params={"language": "en-US"},
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["available"])
        self.assertEqual(payload["transcript"], "check tunnel status")
        self.assertEqual(payload["provider"], "azure")
        self.assertAlmostEqual(payload["confidence"], 0.88)
        self.assertIsNone(payload["reason"])

    @patch("app.azure_stt.transcribe_azure_stt", return_value=None)
    def test_post_stt_falls_back_when_cloud_unavailable(self, _mock_transcribe) -> None:
        operator_presence_settings_store.save_settings(
            {
                **operator_presence_settings_store.load_settings(),
                "privacy_mode": False,
            }
        )
        response = self.client.post(
            "/api/kairo/stt",
            files={"file": ("capture.ogg", io.BytesIO(b"audio"), "audio/ogg")},
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertFalse(payload["available"])
        self.assertEqual(payload["reason"], "cloud_stt_unavailable")
        self.assertEqual(payload["provider"], "browser")


if __name__ == "__main__":
    unittest.main()
