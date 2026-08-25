"""Structured recovery-decision contract for agent failure/blocked cards.

The control plane decides card shape; the frontend renders it faithfully. This
replaces the old pattern where a Lead check-in's plain-text report was
regex-parsed back into an Ask card client-side (apps/console-web/src/lib/
lead-checkin-card.ts's optionsFor()) with no concept of whether the agent
could have safely self-recovered. See docs/ops (AXON-X Smart Agent Cards).

Card types (binding taxonomy — do not blur these):
- working: investigating or performing a safe action right now.
- recovered: a problem was corrected and the original task is continuing.
- blocked: a SINGLE specific missing requirement stops progress. No menu —
  there is nothing to choose between, only one thing to go fix.
- decision_required: two or more materially different paths exist and the
  correct one cannot be determined from evidence. Menu with a recommended
  default, per-option consequence, and a Pause option.
- completed: the task finished with verification.
- failed: safe recovery options were exhausted.

"blocked" vs "decision_required" is the crux of the redesign: a missing
workspace-delivery config, a missing credential, an unpaid invoice — none of
these are business decisions with competing options, they are one missing
thing. Rendering them as a 4-button "how should the Lead handle this?" menu
(the bug this module fixes) invents a decision that does not exist.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Literal

CardType = Literal["working", "recovered", "blocked", "decision_required", "completed", "failed"]

# card types that must never carry an interactive options menu -- rendering
# choices on these would recreate the exact "invented decision" bug this
# contract exists to prevent.
_CARD_TYPES_WITHOUT_CHOICES: frozenset[CardType] = frozenset(
    {"working", "recovered", "blocked", "completed", "failed"}
)


@dataclass(frozen=True)
class EvidenceRef:
    """A pointer to where a human (or another agent) can verify a claim."""

    label: str
    ref: str


@dataclass(frozen=True)
class RecoveryChoice:
    """One option on a decision_required card.

    expected_result and risk are required on every choice — "list commands"
    without consequences is exactly the vague-question anti-pattern this
    contract replaces.
    """

    id: str
    label: str
    expected_result: str
    risk: str
    recommended: bool = False
    is_pause: bool = False


@dataclass(frozen=True)
class RecoveryDecision:
    card_type: CardType
    summary: str
    classification: str
    operator_action_required: bool
    recommended_action: str
    automatic_next_action: str | None
    actions_attempted: tuple[str, ...] = ()
    evidence: tuple[EvidenceRef, ...] = ()
    confidence: float = 0.5
    retry_eligible: bool = False
    recovery_eligible: bool = False
    escalation_reason: str | None = None
    choices: tuple[RecoveryChoice, ...] = ()

    def __post_init__(self) -> None:
        if self.card_type in _CARD_TYPES_WITHOUT_CHOICES and self.choices:
            raise ValueError(
                f"card_type={self.card_type!r} must not carry choices "
                "(only decision_required renders a menu) — this invariant is "
                "what stops an invented decision from reaching the operator"
            )
        if self.card_type == "decision_required" and not self.choices:
            raise ValueError("decision_required card must include at least one choice")
        if self.card_type == "decision_required":
            recommended = [choice for choice in self.choices if choice.recommended]
            if len(recommended) != 1:
                raise ValueError(
                    "decision_required card must recommend exactly one choice "
                    f"(got {len(recommended)}) — the agent must commit to a "
                    "concrete recommendation, not just list options"
                )
            if not any(choice.is_pause for choice in self.choices):
                raise ValueError(
                    "decision_required card must include a safe 'Pause and "
                    "review later' choice"
                )
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError(f"confidence must be within [0.0, 1.0], got {self.confidence}")

    def to_payload(self) -> dict[str, object]:
        return {
            "card_type": self.card_type,
            "summary": self.summary,
            "classification": self.classification,
            "operator_action_required": self.operator_action_required,
            "recommended_action": self.recommended_action,
            "automatic_next_action": self.automatic_next_action,
            "actions_attempted": list(self.actions_attempted),
            "evidence": [{"label": item.label, "ref": item.ref} for item in self.evidence],
            "confidence": self.confidence,
            "retry_eligible": self.retry_eligible,
            "recovery_eligible": self.recovery_eligible,
            "escalation_reason": self.escalation_reason,
            "choices": [
                {
                    "id": choice.id,
                    "label": choice.label,
                    "expected_result": choice.expected_result,
                    "risk": choice.risk,
                    "recommended": choice.recommended,
                    "is_pause": choice.is_pause,
                }
                for choice in self.choices
            ],
        }


def render_decision_fence(decision: RecoveryDecision) -> str:
    """Render as a :::decision fence, matching the existing :::ask/:::edit/:::tool convention.

    A fence (not a bare JSON blob) so the existing transcript block parser
    (apps/console-web/src/lib/agent-transcript/parse-transcript-blocks.ts,
    which already recognizes :::thinking/:::edit/:::tool/:::ask) can pick this
    up the same way, and so the message stays readable as plain text if a
    caller strips fences.
    """
    body = json.dumps(decision.to_payload(), separators=(",", ":"), sort_keys=True)
    return f"\n:::decision\n{body}\n:::\n"


def decision_from_payload(payload: dict[str, object]) -> RecoveryDecision:
    """Reconstruct a RecoveryDecision from a parsed fence payload (round-trip, used by tests)."""
    choices = tuple(
        RecoveryChoice(
            id=str(item.get("id", "")),
            label=str(item.get("label", "")),
            expected_result=str(item.get("expected_result", "")),
            risk=str(item.get("risk", "")),
            recommended=bool(item.get("recommended", False)),
            is_pause=bool(item.get("is_pause", False)),
        )
        for item in (payload.get("choices") or [])
        if isinstance(item, dict)
    )
    evidence = tuple(
        EvidenceRef(label=str(item.get("label", "")), ref=str(item.get("ref", "")))
        for item in (payload.get("evidence") or [])
        if isinstance(item, dict)
    )
    return RecoveryDecision(
        card_type=payload.get("card_type", "blocked"),  # type: ignore[arg-type]
        summary=str(payload.get("summary", "")),
        classification=str(payload.get("classification", "")),
        operator_action_required=bool(payload.get("operator_action_required", False)),
        recommended_action=str(payload.get("recommended_action", "")),
        automatic_next_action=payload.get("automatic_next_action"),  # type: ignore[arg-type]
        actions_attempted=tuple(str(item) for item in (payload.get("actions_attempted") or [])),
        evidence=evidence,
        confidence=float(payload.get("confidence", 0.5)),  # type: ignore[arg-type]
        retry_eligible=bool(payload.get("retry_eligible", False)),
        recovery_eligible=bool(payload.get("recovery_eligible", False)),
        escalation_reason=payload.get("escalation_reason"),  # type: ignore[arg-type]
        choices=choices,
    )


__all__ = [
    "CardType",
    "EvidenceRef",
    "RecoveryChoice",
    "RecoveryDecision",
    "render_decision_fence",
    "decision_from_payload",
]
