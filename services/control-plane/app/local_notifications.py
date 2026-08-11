"""Bounded desktop notifications for consequential Axon-X run transitions."""

from __future__ import annotations

import os
import shutil
import subprocess
from typing import Any

_NOTIFIABLE_PHASES = frozenset({"approval_required", "blocked", "failed", "review_ready"})


def notification_capability(env: dict[str, str] | None = None) -> dict[str, object]:
    runtime_env = env or dict(os.environ)
    disabled = str(runtime_env.get("AXON_WATCH_NOTIFICATIONS_ENABLED", "1")).lower() in {
        "0", "false", "no", "off"
    }
    binary = shutil.which("notify-send", path=runtime_env.get("PATH"))
    ready = bool(binary and runtime_env.get("DBUS_SESSION_BUS_ADDRESS") and not disabled)
    return {"enabled": ready, "provider": "notify-send" if binary else "unavailable"}


def notify_run_transition(record: dict[str, Any]) -> bool:
    phase = str(record.get("phase") or "").strip().lower()
    if phase not in _NOTIFIABLE_PHASES:
        return False
    capability = notification_capability()
    if not capability["enabled"]:
        return False
    title = {
        "approval_required": "Axon-X needs your approval",
        "review_ready": "Axon-X work is ready for review",
        "blocked": "Axon-X run is blocked",
        "failed": "Axon-X run failed",
    }[phase]
    detail = str(record.get("summary") or record.get("current_step") or record.get("run_id") or "").strip()
    urgency = "critical" if phase in {"approval_required", "blocked", "failed"} else "normal"
    try:
        result = subprocess.run(
            [
                str(shutil.which("notify-send")), "--app-name=Axon-X", f"--urgency={urgency}",
                "--hint=string:sound-name:message-new-instant", title, detail[:240],
            ],
            capture_output=True,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return result.returncode == 0
