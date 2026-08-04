"""Fail-closed safety tiers for bounded Mission Control autonomy.

Maps findings and task text to auto-safe vs operator-gated decisions.
``risk`` on the task ledger carries the decision:
  normal / low / approved → auto_safe (continuous workers may lease)
  high / critical / dangerous → operator_gated (must not auto-lease)
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Any, Literal

AutonomyTier = Literal["auto_safe", "operator_gated", "unclassified"]
AutonomyDecision = Literal["dispatch", "escalate", "skip"]

AUTO_SAFE_RISKS = frozenset({"normal", "low", "approved"})
OPERATOR_GATED_RISKS = frozenset({"high", "critical", "dangerous"})
KNOWN_RISKS = AUTO_SAFE_RISKS | OPERATOR_GATED_RISKS

# Phrases that always require a human even when severity looks "normal".
# Avoid bare "token" — connector "token missing" must not false-positive.
_DANGEROUS_MARKERS = (
    "secret",
    "credential",
    "api key",
    "api_key",
    "api token",
    "access token",
    "auth token",
    "bearer token",
    "github token",
    "gh_token",
    "vault token",
    "password",
    "vault",
    "force push",
    "force-push",
    "protected branch",
    "merge to master",
    "merge to main",
    "merge to dev",
    "production deploy",
    "deploy to production",
    "release to production",
    "drop table",
    "rm -rf",
    "git reset --hard",
    "git clean -fd",
    "git clean -xdf",
    "truncate table",
    "delete from ",
    "delete database",
    "spend limit",
    "usage cap",
    "external publish",
    "public post",
    "approve run",
    "full access",
    "policy change",
    "permission change",
)

_SAFETY_INSTRUCTION_PHRASES = (
    "do not touch secrets, production, protected merges, or spend caps",
    "never touch secrets, production, protected merges, or spend caps",
)

# Connector/status copy that mentions "token" without requesting secret mutation.
_TOKEN_STATUS_ALLOWLIST = (
    "token missing",
    "auth=missing",
    "auth missing",
    "tunnel token missing",
    "no token configured",
)

_GITHUB_EMAIL_CI_RE = re.compile(
    r"(?is)email needs follow-up:.*"
    r"(pr run failed|check[- ]suites|github\.com|.*/.*\].*(?:ci|pipeline|workflow))"
)
_GITHUB_EMAIL_SIGNAL_RE = re.compile(
    r"(?i)signal_email_.*(check-suites|pull_|actions|_github)"
)

# Investigatory criticals VAXON may auto-dispatch under Full autonomy
# (no secrets / production mutation — those stay operator-gated).
_INVESTIGATORY_CRITICAL_RE = re.compile(
    r"(?i)\b("
    r"sentry|fast\s*gate|typecheck|workflow|pipeline|check[- ]suite|"
    r"github\s*actions|android(?:\s+ci|\s+build)?|assembledebug|"
    r"ci(?:\s|/|-)|monitor|probe|crash|exception|ota|canary|"
    r"integration\s*test|unit\s*test|lint"
    r")\b"
)

_SAFE_FINDING_KINDS = frozenset(
    {
        "failed_shift",
        "monitor_alert",
        "connector_degraded",
        "warning_signal",
        "high_signal",
        "open_handoff",
        "file_size_patrol",
        "ci_remediation",
        "stale_ci_signal",
    }
)

_ESCALATE_FINDING_KINDS = frozenset(
    {
        "operator_blocker",
        "critical_signal",
        "pending_approval",
        "dangerous_action",
        "secrets_blocker",
        "production_risk",
    }
)


@dataclass(frozen=True)
class AutonomyPolicyDecision:
    tier: AutonomyTier
    decision: AutonomyDecision
    risk: str
    reason: str
    ask_operator: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def normalize_task_risk(risk: str | None) -> str:
    cleaned = str(risk or "normal").strip().lower() or "normal"
    if cleaned in KNOWN_RISKS:
        return cleaned
    # Fail closed: unknown risk labels cannot auto-lease.
    return "high"


def tier_for_risk(risk: str | None) -> AutonomyTier:
    cleaned = str(risk or "").strip().lower()
    if cleaned in AUTO_SAFE_RISKS:
        return "auto_safe"
    if cleaned in OPERATOR_GATED_RISKS:
        return "operator_gated"
    return "unclassified"


def text_looks_dangerous(*parts: str | None) -> bool:
    hay = " ".join(str(part or "") for part in parts).lower()
    for phrase in _SAFETY_INSTRUCTION_PHRASES:
        hay = hay.replace(phrase, "")
    for phrase in _TOKEN_STATUS_ALLOWLIST:
        hay = hay.replace(phrase, "")
    return any(marker in hay for marker in _DANGEROUS_MARKERS)


def is_github_email_ci_noise(*, title: str = "", detail: str = "", dedupe_key: str = "") -> bool:
    """True for GitHub notification emails that must not auto-open attend tasks."""
    blob = f"{title}\n{detail}\n{dedupe_key}"
    if _GITHUB_EMAIL_CI_RE.search(blob):
        return True
    return bool(_GITHUB_EMAIL_SIGNAL_RE.search(blob))


def is_investigatory_critical(*, title: str = "", detail: str = "") -> bool:
    """True when a critical is safe to investigate automatically (CI/Sentry/monitor)."""
    blob = f"{title}\n{detail}".strip()
    if not blob:
        return False
    if text_looks_dangerous(title, detail):
        return False
    return bool(_INVESTIGATORY_CRITICAL_RE.search(blob))


def classify_attention_item(
    *,
    kind: str,
    title: str = "",
    detail: str = "",
    severity: str = "",
    escalate_only: bool = False,
    risk_hint: str | None = None,
    dedupe_key: str = "",
) -> AutonomyPolicyDecision:
    """Classify one Mission Control attention item for auto-attend."""
    cleaned_kind = str(kind or "").strip().lower()
    severity_l = str(severity or "").strip().lower()
    blob_title = str(title or "").strip()
    blob_detail = str(detail or "").strip()

    # Child-repo CI mail is route noise for Full attend — never auto-lease.
    if severity_l != "critical" and cleaned_kind in {
        "warning_signal",
        "high_signal",
        "monitor_alert",
    } and is_github_email_ci_noise(
        title=blob_title,
        detail=blob_detail,
        dedupe_key=dedupe_key,
    ):
        return AutonomyPolicyDecision(
            tier="auto_safe",
            decision="skip",
            risk="normal",
            reason="email_ci_noise_no_dispatch",
            ask_operator=False,
        )

    # Secrets / production markers always gate — even for investigatory CI titles.
    if text_looks_dangerous(blob_title, blob_detail, cleaned_kind):
        return AutonomyPolicyDecision(
            tier="operator_gated",
            decision="escalate",
            risk="dangerous",
            reason="dangerous_marker",
            ask_operator=True,
        )

    # Critical CI/Sentry/monitor spikes: VAXON investigates without yanking the operator.
    if (
        not escalate_only
        and (cleaned_kind == "critical_signal" or severity_l == "critical")
        and is_investigatory_critical(title=blob_title, detail=blob_detail)
    ):
        return AutonomyPolicyDecision(
            tier="auto_safe",
            decision="dispatch",
            risk="normal",
            reason="bounded_auto:investigate_critical",
            ask_operator=False,
        )

    if escalate_only or cleaned_kind in _ESCALATE_FINDING_KINDS:
        return AutonomyPolicyDecision(
            tier="operator_gated",
            decision="escalate",
            risk="critical" if severity_l == "critical" else "high",
            reason=f"escalation_required:{cleaned_kind or 'unknown'}",
            ask_operator=True,
        )

    if severity_l == "critical" or cleaned_kind == "critical_signal":
        return AutonomyPolicyDecision(
            tier="operator_gated",
            decision="escalate",
            risk="critical",
            reason="critical_severity",
            ask_operator=True,
        )

    if risk_hint is not None:
        normalized = normalize_task_risk(risk_hint)
        tier = tier_for_risk(normalized)
        if tier != "auto_safe":
            return AutonomyPolicyDecision(
                tier="operator_gated",
                decision="escalate",
                risk=normalized,
                reason="risk_hint_gated",
                ask_operator=True,
            )

    if cleaned_kind in _SAFE_FINDING_KINDS or severity_l in {"", "info", "low", "medium", "high", "warning"}:
        # high (non-critical) warnings may auto-dispatch inspection/fix tasks
        return AutonomyPolicyDecision(
            tier="auto_safe",
            decision="dispatch",
            risk="normal" if cleaned_kind != "connector_degraded" else "normal",
            reason=f"bounded_auto:{cleaned_kind or 'generic'}",
            ask_operator=False,
        )

    return AutonomyPolicyDecision(
        tier="unclassified",
        decision="escalate",
        risk="high",
        reason="unclassified_fail_closed",
        ask_operator=True,
    )


def attention_finding_auto_dispatches(finding: Any) -> bool:
    """True only when a Lead-style finding passes the central safety policy."""
    decision = classify_attention_item(
        kind=str(getattr(finding, "kind", "") or ""),
        title=str(getattr(finding, "title", "") or ""),
        detail=str(getattr(finding, "detail", "") or ""),
        escalate_only=bool(getattr(finding, "escalate_only", False)),
        dedupe_key=str(getattr(finding, "dedupe_key", "") or ""),
    )
    return decision.decision == "dispatch" and not decision.ask_operator


def task_allows_autonomous_lease(task: dict[str, Any] | None) -> AutonomyPolicyDecision:
    """Fail-closed lease gate used by scheduler / claim paths."""
    if not isinstance(task, dict):
        return AutonomyPolicyDecision(
            tier="unclassified",
            decision="skip",
            risk="high",
            reason="missing_task",
            ask_operator=True,
        )
    risk = normalize_task_risk(str(task.get("risk") or ""))
    tier = tier_for_risk(risk)
    if risk == "approved":
        from app.persistence import autonomous_attention_store

        receipt_id = str(task.get("approval_receipt_id") or "").strip()
        receipt = autonomous_attention_store.get_receipt(receipt_id)
        valid = (
            isinstance(receipt, dict)
            and receipt.get("status") == "resolved"
            and receipt.get("resolution") == "approved"
            and str(receipt.get("task_id") or "") == str(task.get("task_id") or "")
        )
        if valid:
            return AutonomyPolicyDecision(
                tier="auto_safe",
                decision="dispatch",
                risk=risk,
                reason="operator_approved",
                ask_operator=False,
            )
        return AutonomyPolicyDecision(
            tier="operator_gated",
            decision="skip",
            risk="high",
            reason="invalid_approval_provenance",
            ask_operator=True,
        )
    if tier == "auto_safe" and not text_looks_dangerous(
        str(task.get("goal") or ""),
        str(task.get("acceptance_criteria") or ""),
    ):
        return AutonomyPolicyDecision(
            tier="auto_safe",
            decision="dispatch",
            risk=risk,
            reason="risk_auto_safe",
            ask_operator=False,
        )
    if text_looks_dangerous(
        str(task.get("goal") or ""),
        str(task.get("acceptance_criteria") or ""),
    ):
        return AutonomyPolicyDecision(
            tier="operator_gated",
            decision="escalate",
            risk="dangerous",
            reason="dangerous_task_text",
            ask_operator=True,
        )
    return AutonomyPolicyDecision(
        tier="operator_gated" if tier == "operator_gated" else "unclassified",
        decision="skip",
        risk=risk if risk in OPERATOR_GATED_RISKS else "high",
        reason="lease_blocked_fail_closed",
        ask_operator=True,
    )


def assert_task_lease_allowed(task: dict[str, Any] | None) -> None:
    """Raise ValueError when a task must not be auto-leased."""
    decision = task_allows_autonomous_lease(task)
    if decision.tier != "auto_safe" or decision.decision != "dispatch":
        raise ValueError(
            f"autonomous lease refused ({decision.reason}; "
            f"tier={decision.tier}; risk={decision.risk})"
        )


__all__ = [
    "AUTO_SAFE_RISKS",
    "OPERATOR_GATED_RISKS",
    "AutonomyDecision",
    "AutonomyPolicyDecision",
    "AutonomyTier",
    "attention_finding_auto_dispatches",
    "assert_task_lease_allowed",
    "classify_attention_item",
    "is_github_email_ci_noise",
    "normalize_task_risk",
    "task_allows_autonomous_lease",
    "text_looks_dangerous",
    "tier_for_risk",
]
