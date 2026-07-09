from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from tests.support.control_plane_db import isolate_control_plane_db

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.kairo_voice import (  # noqa: E402
    _HISTORY,
    generate_spoken_line,
    narration_allows_event,
    normalize_spoken_line,
    should_use_runtime_for_event,
)
from app.main import app  # noqa: E402
from app.persistence import operator_presence_settings_store, run_store  # noqa: E402


class KairoVoicePolicyTests(unittest.TestCase):
    def setUp(self) -> None:
        _HISTORY.clear()

    def test_fallback_lines_vary_within_session(self) -> None:
        with patch("app.kairo_voice._try_runtime_line", return_value=None):
            first = generate_spoken_line(
                event_type="agent_start",
                session_id="voice-test-session",
            )
            second = generate_spoken_line(
                event_type="agent_start",
                session_id="voice-test-session",
            )
        self.assertNotEqual(first["line"], second["line"])
        self.assertEqual(first["source"], "fallback")
        self.assertEqual(second["source"], "fallback")

    def test_narration_allows_event_respects_levels(self) -> None:
        self.assertFalse(narration_allows_event("agent_start", "off"))
        self.assertTrue(narration_allows_event("agent_start", "minimal"))
        self.assertFalse(narration_allows_event("tool", "conversational"))
        self.assertTrue(narration_allows_event("done", "conversational"))
        self.assertFalse(narration_allows_event("tool", "minimal"))

    def test_agent_start_fallback_ignores_active_file(self) -> None:
        with patch("app.kairo_voice._try_runtime_line", return_value=None):
            payload = generate_spoken_line(
                event_type="agent_start",
                context={"active_file": "README.md", "operator_prompt": "fix the terminal"},
                session_id="fallback-readme-test",
            )
        self.assertNotIn("README", payload["line"])
        self.assertEqual(payload["source"], "fallback")

    def test_contextual_fallback_uses_operator_prompt(self) -> None:
        with patch("app.kairo_voice._try_runtime_line", return_value=None):
            start = generate_spoken_line(
                event_type="agent_start",
                context={"operator_prompt": "it seems like your report was cut short - please continue"},
                session_id="contextual-fallback",
            )
            done = generate_spoken_line(
                event_type="done",
                context={"operator_prompt": "What do you think the project needs?"},
                session_id="contextual-fallback",
            )
        self.assertIn("report", start["line"].lower())
        self.assertIn("answer", done["line"].lower())

    def test_failed_outcome_does_not_claim_all_set(self) -> None:
        with patch("app.kairo_voice._try_runtime_line", return_value=None):
            payload = generate_spoken_line(
                event_type="failed",
                context={
                    "operator_prompt": "continue the dashpro work",
                    "outcome": "failed",
                    "failure_summary": (
                        "Lane B (agent) cannot start because no CLI runtime is ready: "
                        "ActionRequiredError: You're out of usage."
                    ),
                },
                session_id="failed-outcome",
            )
            done_with_flag = generate_spoken_line(
                event_type="done",
                context={
                    "operator_prompt": "continue the dashpro work",
                    "outcome": "failed",
                    "failure_summary": "Codex/OpenAI API key was rejected",
                },
                session_id="failed-outcome-done",
            )
        self.assertNotIn("all set", payload["line"].lower())
        self.assertNotIn("review when", payload["line"].lower())
        self.assertIn("couldn't start", payload["line"].lower())
        self.assertNotIn("all set", done_with_flag["line"].lower())
        self.assertIn("couldn't start", done_with_flag["line"].lower())

    def test_approval_literal_bypasses_runtime(self) -> None:
        with patch("app.kairo_voice._try_runtime_line", return_value="Model paraphrase."):
            payload = generate_spoken_line(
                event_type="approval_literal",
                context={"literal_line": "2 approvals waiting for your review."},
                narration="conversational",
            )
        self.assertEqual(payload["line"], "2 approvals waiting for your review.")
        self.assertEqual(payload["source"], "literal")

    def test_runtime_used_for_minimal_and_conversational(self) -> None:
        self.assertTrue(should_use_runtime_for_event("done", "minimal"))
        self.assertTrue(should_use_runtime_for_event("agent_start", "conversational"))
        self.assertFalse(should_use_runtime_for_event("done", "off"))
        self.assertFalse(should_use_runtime_for_event("conversation_reply", "minimal"))
        self.assertTrue(should_use_runtime_for_event("conversation_reply", "conversational"))

    def test_conversation_reply_fallback_uses_literal(self) -> None:
        with patch("app.kairo_voice._try_runtime_line", return_value=None):
            payload = generate_spoken_line(
                event_type="conversation_reply",
                context={
                    "fallback": "Two approvals waiting — I'd open Attention first.",
                    "reply": "Two approvals waiting — I'd open Attention first.",
                    "operator_prompt": "any approvals?",
                },
                session_id="conversation-reply-fallback",
                narration="minimal",
            )
        self.assertIn("Two approvals", payload["line"])
        self.assertEqual(payload["source"], "fallback")

    def test_normalize_spoken_line_strips_agent_stream_blocks(self) -> None:
        raw = (
            ":::thinking\nInvestigating the spike.\n:::\n"
            ":::tool Read scripts/ops/audit-supabase-storage.mjs\n\n"
            "From my side right now, DashPro is not spiking — systems nominal.\n\n"
            "If you are seeing a spike in Axon, the repo points at Supabase storage."
        )
        line = normalize_spoken_line(raw)
        self.assertNotIn(":::", line)
        self.assertNotIn("scripts/ops", line)
        self.assertIn("DashPro is not spiking", line)
        self.assertIn("Supabase storage", line)

    def test_normalize_spoken_line_dedupes_repeated_sentences(self) -> None:
        raw = (
            "I'll narrow it. From my side right now DashPro is not spiking. "
            "If you are seeing a spike in Supabase or Axon quota, the repo points at storage, not the database. "
            "If you are seeing a spike in Supabase or Axon quota, the repo points at storage, not the database."
        )
        line = normalize_spoken_line(raw)
        self.assertEqual(line.count("If you are seeing a spike in Supabase"), 1)

    def test_normalize_spoken_line_restores_missing_sentence_space(self) -> None:
        raw = "I'll narrow it.From my side right now DashPro is not spiking."
        line = normalize_spoken_line(raw)
        self.assertEqual(
            "I'll narrow it. From my side right now DashPro is not spiking.",
            line,
        )


class KairoSpeakApiTests(unittest.TestCase):
    def setUp(self) -> None:
        isolate_control_plane_db(self, run_store)
        self.client = TestClient(app)
        self.addCleanup(self.client.close)

    def test_speak_skipped_when_narration_off(self) -> None:
        operator_presence_settings_store.save_settings(
            {
                **operator_presence_settings_store.load_settings(),
                "kairo_narration": "off",
            }
        )
        response = self.client.post(
            "/api/kairo/speak",
            json={"event_type": "agent_start", "session_id": "api-test"},
        )
        self.assertEqual(200, response.status_code)
        payload = response.json()
        self.assertEqual("", payload["line"])
        self.assertEqual("skipped", payload["source"])

    def test_speak_returns_fallback_line_when_narration_minimal(self) -> None:
        response = self.client.post(
            "/api/kairo/speak",
            json={"event_type": "agent_start", "session_id": "api-test-minimal"},
        )
        self.assertEqual(200, response.status_code)
        payload = response.json()
        self.assertTrue(payload["line"])
        self.assertIn(payload["source"], {"fallback", "model"})


if __name__ == "__main__":
    unittest.main()
