from __future__ import annotations

import unittest

from tests.support.control_plane_app_loader import prepare_control_plane_imports


class SignalExplanationTests(unittest.TestCase):
    def setUp(self) -> None:
        prepare_control_plane_imports()
        from app.signal_explanation import resolve_signal_explanation  # noqa: WPS433

        self.resolve_signal_explanation = resolve_signal_explanation

    def test_rejected_auth_token_resolves_to_vault_next_step(self) -> None:
        explanation = self.resolve_signal_explanation(
            {"severity": "critical", "summary": "Sentry API rejected the auth token"}
        )
        self.assertIsNotNone(explanation)
        self.assertIn("stopped working", explanation.plain_explanation)
        self.assertIn("Vault", explanation.next_step)
        self.assertEqual("you", explanation.owner_hint)

    def test_billing_blocker_resolves_to_billing_next_step(self) -> None:
        explanation = self.resolve_signal_explanation(
            {
                "severity": "critical",
                "summary": "GitHub Actions billing blocker: job never started (runner_id=0)",
            }
        )
        self.assertIsNotNone(explanation)
        self.assertIn("budget", explanation.plain_explanation)
        self.assertIn("billing", explanation.next_step.lower())

    def test_ssh_hostname_failure_resolves_to_runtime_settings_next_step(self) -> None:
        explanation = self.resolve_signal_explanation(
            {
                "severity": "high",
                "summary": "blocked: ssh: Could not resolve hostname github-axon-control-ops",
            }
        )
        self.assertIsNotNone(explanation)
        self.assertIn("SSH", explanation.next_step)

    def test_no_publishable_changes_resolves_to_safe_complete_next_step(self) -> None:
        explanation = self.resolve_signal_explanation(
            {
                "severity": "normal",
                "summary": "full-access worker produced no publishable changes (no changes)",
            }
        )
        self.assertIsNotNone(explanation)
        self.assertEqual("agent", explanation.owner_hint)

    def test_unrecognized_summary_returns_none(self) -> None:
        explanation = self.resolve_signal_explanation(
            {"severity": "critical", "summary": "Something totally novel and undiagnosed"}
        )
        self.assertIsNone(explanation)

    def test_non_critical_auth_wording_without_severity_match_returns_none(self) -> None:
        # The auth-token pattern is deliberately gated on severity=critical so a
        # low-severity signal that happens to mention "unauthorized" in passing
        # doesn't get a confident-sounding explanation it hasn't earned.
        explanation = self.resolve_signal_explanation(
            {"severity": "info", "summary": "Note: previous run saw an unauthorized retry, now recovered"}
        )
        self.assertIsNone(explanation)


if __name__ == "__main__":
    unittest.main()
