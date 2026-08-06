"""VAXON fleet self-heal: failure classification and fingerprinting."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.fleet_self_heal.classify import (  # noqa: E402
    build_fingerprint,
    classify_failure_signature,
    quick_fleet_infra_marker_match,
)

# Same fixtures used in tests/test_scheduler_generic_retry_backoff.py's
# gate-handled/shift-continuation coverage — the two systems must agree on
# what's already handled, or a fleet-infra dispatch would race the existing
# scheduler gates for the same failure.
_GATE_HANDLED_DETAILS = (
    "Out of usage — increase limits in Cursor",
    "Credit balance is too low",
    "ActionRequiredError: You have an unpaid invoice",
    "Cursor is installed but not signed in. Run `cursor agent login` or unlock /vault.",
    "Cursor CLI exited with status 143.",
    "Cursor CLI exited with status 137.",
    "Run interrupted by control-plane restart.",
    "Runtime execution stopped by operator before the shift finished.",
)


class ClassifyFailureSignatureTests(unittest.TestCase):
    def test_gate_handled_failures_never_route_to_fleet_infra(self) -> None:
        for detail in _GATE_HANDLED_DETAILS:
            signature = classify_failure_signature(detail=detail)
            self.assertEqual(
                "gate_handled", signature.category, f"should defer to existing gates: {detail}"
            )
            self.assertEqual("", signature.fingerprint)

    def test_traceback_inside_control_plane_is_high_confidence_fleet_infra(self) -> None:
        detail = (
            'Traceback (most recent call last):\n'
            '  File "/home/edp/axon-nvme/repos/axon-watch/services/control-plane/app/'
            'workspace_agents/agent_sandbox.py", line 214, in build_bwrap_command\n'
            "    raise SandboxConfigurationError(...)\n"
        )
        signature = classify_failure_signature(detail=detail)
        self.assertEqual("fleet_infra", signature.category)
        self.assertEqual("high", signature.confidence)
        self.assertEqual(
            "services/control-plane/app/workspace_agents/agent_sandbox.py", signature.file_hint
        )
        self.assertEqual("workspace_agents.agent_sandbox", signature.subsystem)
        self.assertTrue(signature.fingerprint.startswith("fleetbug:workspace_agents.agent_sandbox:"))

    def test_phrase_marker_is_medium_confidence_fleet_infra(self) -> None:
        signature = classify_failure_signature(
            detail="Lane B agent fallback reply generated (maximum recursion depth exceeded; ...)"
        )
        self.assertEqual("fleet_infra", signature.category)
        self.assertEqual("medium", signature.confidence)
        self.assertEqual("cursor_recursion", signature.subsystem)
        self.assertNotEqual("", signature.fingerprint)

    def test_fingerprint_is_stable_across_different_raw_text_same_marker(self) -> None:
        first = classify_failure_signature(
            detail="run_a1b2c3: Lane B agent fallback reply generated (maximum recursion depth exceeded)"
        )
        second = classify_failure_signature(
            detail="run_ffeeaa99: fallback (maximum recursion depth exceeded; other noise)"
        )
        self.assertEqual(first.fingerprint, second.fingerprint)

    def test_fingerprint_differs_across_different_markers(self) -> None:
        recursion = classify_failure_signature(detail="maximum recursion depth exceeded")
        install = classify_failure_signature(detail="Error: Could not install cursor-agent.")
        self.assertNotEqual(recursion.fingerprint, install.fingerprint)

    def test_acceptance_failure_routes_to_workspace_code(self) -> None:
        signature = classify_failure_signature(
            detail="acceptance=fail · failed_checks=lint,tests; policy=strict"
        )
        self.assertEqual("workspace_code", signature.category)
        self.assertEqual("", signature.fingerprint)

    def test_unrecognized_text_routes_to_unknown_without_dispatch(self) -> None:
        signature = classify_failure_signature(detail="something entirely novel happened")
        self.assertEqual("unknown", signature.category)
        self.assertEqual("", signature.fingerprint)

    def test_build_fingerprint_is_deterministic(self) -> None:
        first = build_fingerprint(subsystem="a", marker="b", file_hint="c")
        second = build_fingerprint(subsystem="a", marker="b", file_hint="c")
        self.assertEqual(first, second)
        self.assertTrue(first.startswith("fleetbug:a:"))


class QuickFleetInfraMarkerMatchTests(unittest.TestCase):
    def test_matches_known_marker_phrase(self) -> None:
        self.assertTrue(quick_fleet_infra_marker_match("maximum recursion depth exceeded"))

    def test_does_not_match_gate_handled_text_even_with_incidental_overlap(self) -> None:
        self.assertFalse(quick_fleet_infra_marker_match("Out of usage — increase limits in Cursor"))

    def test_does_not_match_unrelated_text(self) -> None:
        self.assertFalse(quick_fleet_infra_marker_match("acceptance=fail · lint failed"))

    def test_safe_on_truncated_180_char_strings(self) -> None:
        # Truncated mid-word, no traceback available — must still match on
        # the phrase alone without attempting path/regex scanning.
        truncated = ("Lane B agent fallback reply generated (maximum recursion depth "
                     "exceeded; Cursor Cloud Agent unavailable; Codex Cloud Task u")
        self.assertTrue(quick_fleet_infra_marker_match(truncated))

    def test_gate_handled_marker_wins_when_composite_message_has_both(self) -> None:
        # A joined fallback-chain message can legitimately contain both a
        # fleet-infra marker (recursion) and a gate-handled marker (auth) from
        # different runtime attempts. Conservative default: defer to the
        # existing gate rather than risk VAXON dispatching on an ambiguous
        # composite where the primary driver may be the auth failure.
        composite = ("Lane B agent fallback reply generated (maximum recursion depth "
                     "exceeded; Cursor Cloud Agent unavailable; Codex/OpenAI API key was "
                     "rejected. Fix keys in /vault or run `codex login`.; Codex Cloud Task u")
        self.assertFalse(quick_fleet_infra_marker_match(composite))


if __name__ == "__main__":
    unittest.main()
