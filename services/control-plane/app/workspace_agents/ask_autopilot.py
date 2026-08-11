"""Auto-mode resolution policy for employee ask cards.

The UI ask card is still the right shape for true operator decisions. In Full
Auto, though, a worker should not park a leased task on a reversible engineering
choice such as "keep investigating" or "clear cache". This module keeps that
boundary explicit and auditable.
"""

from __future__ import annotations

from dataclasses import dataclass
import re

_ASK_FENCE_RE = re.compile(
    r"^:::ask\b(?P<header>.*?)\n(?P<body>.*?)(?:^:::\s*$|\Z)",
    re.MULTILINE | re.DOTALL,
)
_OPTION_PIPE_RE = re.compile(r"^\s*[-*]\s+(\d+)\s*\|\s+(.+?)\s*$")
_OPTION_DASH_RE = re.compile(r"^\s*[-*]\s+(\d+)[.)]\s+(.+?)\s*$")
_OPTION_NUMBER_RE = re.compile(r"^\s*(\d+)[.)]\s+(.+?)\s*$")

_UNSAFE_MARKERS = (
    "production",
    "prod",
    "deploy",
    "release",
    "merge",
    "push",
    "commit",
    "force-push",
    "delete",
    "remove data",
    "drop table",
    "wipe",
    "overwrite",
    "credential",
    "secret",
    "token",
    "password",
    "api key",
    "billing",
    "payment",
    "spend",
    "purchase",
    "legal",
    "customer",
    "school account",
    "which account",
    "user data",
)

_SAFE_PROGRESS_MARKERS = (
    "continue",
    "proceed",
    "investigate",
    "diagnose",
    "trace",
    "fix",
    "harden",
    "cache",
    "refresh",
    "reversible",
    "safe",
    "smallest",
    "targeted",
    "verify",
    "test",
    "both",
    "unsure",
)

_AVOID_OPTION_MARKERS = (
    "force",
    "production",
    "prod",
    "deploy",
    "release",
    "merge",
    "push",
    "commit",
    "delete",
    "credential",
    "secret",
    "token",
    "password",
    "billing",
    "payment",
    "spend",
    "specific change",
    "need intended",
    "need operator",
)


@dataclass(frozen=True)
class AskOption:
    id: str
    label: str


@dataclass(frozen=True)
class AutoAskResolution:
    prompt: str
    option: AskOption
    answer_text: str
    reason: str

    @property
    def receipt_summary(self) -> str:
        return (
            "Auto mode resolved safe ask card: "
            f"Selected option {self.option.id}: {self.option.label} — {self.reason}"
        )


@dataclass(frozen=True)
class OperatorAskEscalation:
    """A real decision that Auto must not choose, but VAXON must surface."""

    prompt: str
    options: tuple[AskOption, ...]
    reason: str

    @property
    def detail(self) -> str:
        choices = "; ".join(f"{option.id}. {option.label}" for option in self.options)
        return f"{self.reason} Choices: {choices}".strip()


def _clean(text: object) -> str:
    return " ".join(str(text or "").split()).strip()


def _parse_option(line: str) -> AskOption | None:
    for regex in (_OPTION_PIPE_RE, _OPTION_DASH_RE, _OPTION_NUMBER_RE):
        match = regex.match(line)
        if match is None:
            continue
        option_id = _clean(match.group(1))
        label = _clean(match.group(2).replace("*", ""))
        if option_id and label:
            return AskOption(id=option_id, label=label)
    return None


def parse_latest_ask_card(content: str) -> tuple[str, list[AskOption]] | None:
    matches = list(_ASK_FENCE_RE.finditer(str(content or "")))
    if not matches:
        return None
    match = matches[-1]
    header = _clean(match.group("header"))
    body_lines = str(match.group("body") or "").splitlines()
    options: list[AskOption] = []
    prompt_lines: list[str] = []
    for raw in body_lines:
        option = _parse_option(raw)
        if option is not None:
            options.append(option)
            continue
        cleaned = _clean(raw)
        if cleaned and cleaned != ":::":
            prompt_lines.append(cleaned)
    prompt = header or next((line for line in prompt_lines if line.endswith("?")), "")
    if not prompt:
        prompt = "Choose an option to continue"
    return prompt, options


def _contains_any(text: str, markers: tuple[str, ...]) -> bool:
    lowered = text.lower()
    return any(marker in lowered for marker in markers)


def _option_score(option: AskOption) -> int:
    label = option.label.lower()
    score = 0
    for index, marker in enumerate(_SAFE_PROGRESS_MARKERS):
        if marker in label:
            score += 20 - min(index, 15)
    if "unsure" in label and ("harden" in label or "continue" in label):
        score += 12
    if "both" in label:
        score += 5
    if _contains_any(label, _AVOID_OPTION_MARKERS):
        score -= 100
    try:
        # Earlier options are usually the model's preferred path; keep this a
        # small tiebreaker only.
        score -= max(0, int(option.id) - 1)
    except ValueError:
        score -= 3
    return score


def maybe_resolve_safe_ask(
    content: str,
    *,
    auto_mode_enabled: bool,
) -> AutoAskResolution | None:
    if not auto_mode_enabled:
        return None
    parsed = parse_latest_ask_card(content)
    if parsed is None:
        return None
    prompt, options = parsed
    if not options:
        return None
    combined = " ".join([prompt, *[option.label for option in options]])
    if _contains_any(combined, _UNSAFE_MARKERS):
        return None
    candidates = [
        option
        for option in options
        if _contains_any(option.label, _SAFE_PROGRESS_MARKERS)
        and not _contains_any(option.label, _AVOID_OPTION_MARKERS)
    ]
    if not candidates:
        return None
    selected = sorted(candidates, key=_option_score, reverse=True)[0]
    reason = "safe/reversible engineering continuation while Auto mode is enabled"
    answer = (
        f"Selected option {selected.id}: {selected.label}\n"
        f"(answer to: {prompt})\n\n"
        "Auto mode selected this as the safest reversible engineering continuation. "
        "Continue the leased task now; implement the smallest safe fix, run targeted "
        "verification, and report concrete receipts instead of asking again."
    )
    return AutoAskResolution(
        prompt=prompt,
        option=selected,
        answer_text=answer,
        reason=reason,
    )


def unresolved_operator_ask(
    content: str,
    *,
    auto_mode_enabled: bool,
) -> OperatorAskEscalation | None:
    """Return a durable VAXON escalation for an ask Auto cannot safely answer.

    Full Auto is deliberately not authority to create identities, release code,
    spend money, or perform destructive actions. It must still raise the exact
    question globally—rather than leaving it hidden in one employee thread.
    """
    parsed = parse_latest_ask_card(content)
    if parsed is None:
        return None
    prompt, options = parsed
    if not options or maybe_resolve_safe_ask(content, auto_mode_enabled=auto_mode_enabled):
        return None
    reason = (
        "Auto mode did not choose this because it requires an operator decision."
        if auto_mode_enabled
        else "Worker requires an operator decision."
    )
    return OperatorAskEscalation(prompt=prompt, options=tuple(options), reason=reason)


def escalate_unresolved_operator_ask(
    content: str,
    *,
    employee_name: str,
    employee_role: str,
    workspace_id: str,
    task_id: str,
    run_id: str,
) -> bool:
    """Persist a worker's unsafe ask as a visible VAXON decision."""
    from app.persistence import autonomous_attention_store
    from app.persistence import worker_scheduler_settings_store

    operator_ask = unresolved_operator_ask(
        content,
        auto_mode_enabled=bool(
            worker_scheduler_settings_store.load_settings().get("scheduler_enabled")
        ),
    )
    if operator_ask is None:
        return False
    autonomous_attention_store.append_receipt(
        kind="worker_ask",
        decision="escalate",
        tier="operator_decision",
        risk="high",
        title=f"{employee_name} needs a decision: {operator_ask.prompt}",
        detail=operator_ask.detail,
        dedupe_key=f"worker-ask:{run_id}",
        workspace_id=workspace_id,
        task_id=task_id or None,
        ask_operator=True,
        payload={
            "owner_role": employee_role.strip().lower(),
            "run_id": run_id,
            "prompt": operator_ask.prompt,
            "options": [
                {"id": option.id, "label": option.label}
                for option in operator_ask.options
            ],
        },
    )
    return True
