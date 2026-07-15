"""Bounded autonomy tiers for VAXON voice-initiated actions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from app.chat.command_intent import (
    AUTO_COMPLETE_COMMAND_INTENTS,
    classify_command,
    expand_command_shortcuts,
    is_reversible_shell_command,
)

VoiceActionTier = Literal["reversible_auto", "approval_gated", "unsupported"]


@dataclass(frozen=True)
class VoiceActionTierDecision:
    tier: VoiceActionTier
    intent: str
    requires_approval: bool
    auto_execute: bool
    reason: str


def resolve_voice_action_tier(content: str) -> VoiceActionTierDecision:
    """Classify a voice command into auto vs approval-gated autonomy."""
    normalized = expand_command_shortcuts(content.strip())
    intent = classify_command(normalized)
    if intent in AUTO_COMPLETE_COMMAND_INTENTS:
        return VoiceActionTierDecision(
            tier="reversible_auto",
            intent=intent,
            requires_approval=False,
            auto_execute=True,
            reason="allowlisted_reversible",
        )
    if intent == "shell_command" and is_reversible_shell_command(normalized):
        return VoiceActionTierDecision(
            tier="reversible_auto",
            intent=intent,
            requires_approval=False,
            auto_execute=True,
            reason="allowlisted_reversible_shell",
        )
    if intent in {"shell_command", "resume_from_review"}:
        return VoiceActionTierDecision(
            tier="approval_gated",
            intent=intent,
            requires_approval=True,
            auto_execute=False,
            reason="risky_or_write_tier",
        )
    if intent == "unsupported":
        return VoiceActionTierDecision(
            tier="unsupported",
            intent=intent,
            requires_approval=True,
            auto_execute=False,
            reason="unsupported_command",
        )
    return VoiceActionTierDecision(
        tier="approval_gated",
        intent=intent,
        requires_approval=True,
        auto_execute=False,
        reason="default_approval_gate",
    )
