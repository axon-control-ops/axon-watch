"""Safe-auto host action policy: auto / confirm / deny."""

from __future__ import annotations

from typing import Any

ACTION_TIERS = ("auto", "confirm", "deny")

# Metadata observation and reversible convenience actions.
_AUTO_ACTIONS = frozenset(
    {
        "health.snapshot",
        "window.inventory",
        "media.status",
        "artifact.metadata",
        "focus.window",
        "open.path",
        "reveal.path",
        "media.play_pause",
        "media.next",
        "media.previous",
        "volume.adjust",
        "notification.local",
        "bridge.heartbeat",
    }
)

# Exact-effect approval required.
_CONFIRM_ACTIONS = frozenset(
    {
        "clipboard.read",
        "file.read_content",
        "screenshot.capture",
        "file.rename",
        "file.move",
        "session.lock",
        "open.sensitive_path",
        "settings.change",
    }
)

# Hard deny until an operator enables an explicit override flag.
_DENY_ACTIONS = frozenset(
    {
        "file.delete",
        "shell.execute",
        "input.keystroke",
        "camera.capture",
        "mic.capture",
        "secrets.read",
        "home.crawl",
        "artifact.external_upload",
    }
)

_SENSITIVE_PATH_MARKERS = (
    "/.ssh/",
    "/.gnupg/",
    "/.aws/",
    "/.config/gh/",
    "password",
    "secret",
    "credential",
    "keychain",
)


def classify_action(action: str, *, path: str | None = None) -> str:
    """Return auto | confirm | deny for a host action kind."""
    name = str(action or "").strip().lower()
    if not name:
        return "deny"
    if name in _DENY_ACTIONS:
        return "deny"
    if name in _CONFIRM_ACTIONS:
        return "confirm"
    if name in _AUTO_ACTIONS:
        if name in {"open.path", "reveal.path"} and _path_looks_sensitive(path):
            return "confirm"
        return "auto"
    # Unknown actions require confirmation by default.
    return "confirm"


def _path_looks_sensitive(path: str | None) -> bool:
    lowered = str(path or "").strip().lower()
    if not lowered:
        return False
    return any(marker in lowered for marker in _SENSITIVE_PATH_MARKERS)


def evaluate_action_request(
    *,
    action: str,
    path: str | None = None,
    awareness_paused: bool = False,
    deny_overrides_enabled: bool = False,
) -> dict[str, Any]:
    """Decide whether a host action may proceed."""
    if awareness_paused and action not in {"bridge.heartbeat", "health.snapshot"}:
        return {
            "allowed": False,
            "tier": "deny",
            "reason": "host_awareness_paused",
            "requires_approval": False,
        }
    tier = classify_action(action, path=path)
    if tier == "deny" and not deny_overrides_enabled:
        return {
            "allowed": False,
            "tier": "deny",
            "reason": "action_denied_by_policy",
            "requires_approval": False,
        }
    if tier == "deny" and deny_overrides_enabled:
        return {
            "allowed": False,
            "tier": "confirm",
            "reason": "deny_override_requires_approval",
            "requires_approval": True,
        }
    if tier == "confirm":
        return {
            "allowed": False,
            "tier": "confirm",
            "reason": "exact_effect_approval_required",
            "requires_approval": True,
        }
    return {
        "allowed": True,
        "tier": "auto",
        "reason": "safe_auto",
        "requires_approval": False,
    }
