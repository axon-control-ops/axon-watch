"""Structured recovery-decision contract: invariants, fence round-trip."""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.workspace_agents.recovery_decision import (  # noqa: E402
    EvidenceRef,
    RecoveryChoice,
    RecoveryDecision,
    decision_from_payload,
    render_decision_fence,
)


def _blocked() -> RecoveryDecision:
    return RecoveryDecision(
        card_type="blocked",
        summary="Workspace delivery isn't configured for MoveIT.",
        classification="missing_workspace_delivery_config",
        operator_action_required=True,
        recommended_action="Enable workspace delivery for workspace_moveit in config/deployment.env.",
        automatic_next_action=None,
        actions_attempted=("Inspected the failed run", "Checked workspace delivery policy"),
        evidence=(EvidenceRef(label="Failed run", ref="run_eb27cfd30ee4"),),
        confidence=0.9,
        retry_eligible=False,
        recovery_eligible=False,
        escalation_reason="Workspace delivery configuration is a host/operator-level setting the Lead cannot change.",
    )


def _decision_required() -> RecoveryDecision:
    return RecoveryDecision(
        card_type="decision_required",
        summary="Two workspaces both need the same fix; pick which to prioritize.",
        classification="ambiguous_business_choice",
        operator_action_required=True,
        recommended_action="Fix workspace_dashpro first (higher traffic).",
        automatic_next_action=None,
        confidence=0.4,
        choices=(
            RecoveryChoice(
                id="1",
                label="Fix workspace_dashpro first",
                expected_result="dashpro's delivery pipeline is corrected within this shift",
                risk="workspace_tps stays blocked a bit longer",
                recommended=True,
            ),
            RecoveryChoice(
                id="2",
                label="Fix workspace_tps first",
                expected_result="tps's delivery pipeline is corrected within this shift",
                risk="workspace_dashpro stays blocked a bit longer",
            ),
            RecoveryChoice(
                id="3",
                label="Pause and review later",
                expected_result="No change is made until you decide",
                risk="Both workspaces remain blocked",
                is_pause=True,
            ),
        ),
    )


class RecoveryDecisionInvariantTests(unittest.TestCase):
    def test_blocked_card_rejects_choices(self) -> None:
        with self.assertRaisesRegex(ValueError, "must not carry choices"):
            RecoveryDecision(
                card_type="blocked",
                summary="x",
                classification="x",
                operator_action_required=True,
                recommended_action="x",
                automatic_next_action=None,
                choices=(
                    RecoveryChoice(id="1", label="a", expected_result="b", risk="c"),
                ),
            )

    def test_working_recovered_completed_failed_reject_choices(self) -> None:
        for card_type in ("working", "recovered", "completed", "failed"):
            with self.subTest(card_type=card_type):
                with self.assertRaisesRegex(ValueError, "must not carry choices"):
                    RecoveryDecision(
                        card_type=card_type,
                        summary="x",
                        classification="x",
                        operator_action_required=False,
                        recommended_action="x",
                        automatic_next_action=None,
                        choices=(RecoveryChoice(id="1", label="a", expected_result="b", risk="c"),),
                    )

    def test_decision_required_requires_at_least_one_choice(self) -> None:
        with self.assertRaisesRegex(ValueError, "at least one choice"):
            RecoveryDecision(
                card_type="decision_required",
                summary="x",
                classification="x",
                operator_action_required=True,
                recommended_action="x",
                automatic_next_action=None,
            )

    def test_decision_required_requires_exactly_one_recommended_choice(self) -> None:
        # Two choices marked recommended -- isolates the "exactly one" rule
        # from the separate "must have a pause option" rule below.
        with self.assertRaisesRegex(ValueError, "exactly one choice"):
            RecoveryDecision(
                card_type="decision_required",
                summary="x",
                classification="x",
                operator_action_required=True,
                recommended_action="x",
                automatic_next_action=None,
                choices=(
                    RecoveryChoice(id="1", label="a", expected_result="b", risk="c", recommended=True),
                    RecoveryChoice(id="2", label="b", expected_result="b", risk="c", recommended=True),
                    RecoveryChoice(id="3", label="pause", expected_result="b", risk="c", is_pause=True),
                ),
            )

    def test_decision_required_rejects_zero_recommended_choices(self) -> None:
        with self.assertRaisesRegex(ValueError, "exactly one choice"):
            RecoveryDecision(
                card_type="decision_required",
                summary="x",
                classification="x",
                operator_action_required=True,
                recommended_action="x",
                automatic_next_action=None,
                choices=(
                    RecoveryChoice(id="1", label="a", expected_result="b", risk="c"),
                    RecoveryChoice(id="2", label="pause", expected_result="b", risk="c", is_pause=True),
                ),
            )

    def test_decision_required_requires_a_pause_choice(self) -> None:
        with self.assertRaisesRegex(ValueError, "Pause and review later"):
            RecoveryDecision(
                card_type="decision_required",
                summary="x",
                classification="x",
                operator_action_required=True,
                recommended_action="x",
                automatic_next_action=None,
                choices=(
                    RecoveryChoice(id="1", label="a", expected_result="b", risk="c", recommended=True),
                ),
            )

    def test_invalid_card_type_is_rejected_even_with_no_choices(self) -> None:
        # Literal[...] isn't enforced at runtime. Without an explicit check,
        # an invalid card_type matches neither the "without choices" set nor
        # "decision_required", so it would silently bypass every invariant
        # below it — this must fail loudly instead.
        with self.assertRaisesRegex(ValueError, "invalid card_type"):
            RecoveryDecision(
                card_type="not_a_real_card_type",  # type: ignore[arg-type]
                summary="x",
                classification="x",
                operator_action_required=False,
                recommended_action="x",
                automatic_next_action=None,
            )

    def test_confidence_out_of_range_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "confidence"):
            RecoveryDecision(
                card_type="working",
                summary="x",
                classification="x",
                operator_action_required=False,
                recommended_action="x",
                automatic_next_action=None,
                confidence=1.5,
            )

    def test_valid_blocked_card_constructs(self) -> None:
        decision = _blocked()
        self.assertEqual("blocked", decision.card_type)
        self.assertEqual((), decision.choices)

    def test_valid_decision_required_card_constructs(self) -> None:
        decision = _decision_required()
        self.assertEqual(3, len(decision.choices))
        self.assertEqual(1, sum(1 for c in decision.choices if c.recommended))
        self.assertEqual(1, sum(1 for c in decision.choices if c.is_pause))


class RecoveryDecisionFenceTests(unittest.TestCase):
    def test_fence_round_trips_blocked_card(self) -> None:
        original = _blocked()
        fence = render_decision_fence(original)
        self.assertTrue(fence.strip().startswith(":::decision"))
        self.assertTrue(fence.strip().endswith(":::"))
        body = fence.strip().splitlines()[1]
        payload = json.loads(body)
        restored = decision_from_payload(payload)
        self.assertEqual(original, restored)

    def test_fence_round_trips_decision_required_card(self) -> None:
        original = _decision_required()
        fence = render_decision_fence(original)
        body = fence.strip().splitlines()[1]
        payload = json.loads(body)
        restored = decision_from_payload(payload)
        self.assertEqual(original, restored)

    def test_fence_payload_is_valid_json(self) -> None:
        fence = render_decision_fence(_blocked())
        body = fence.strip().splitlines()[1]
        json.loads(body)  # must not raise


if __name__ == "__main__":
    unittest.main()
