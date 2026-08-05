"""VAXON Machine CEO — act on host pulse under Full autonomy."""

from __future__ import annotations

import logging
import os
import signal
from typing import Any

from app.host_context.machine_pulse import build_machine_pulse
from app.host_context.models import normalize_receipt, utc_now_iso
from app.host_context import store
from app.persistence import operator_presence_settings_store

logger = logging.getLogger(__name__)


def _autonomy_full() -> bool:
    settings = operator_presence_settings_store.load_settings()
    return str(settings.get("autonomy_mode") or "").strip().lower() == "full"


def run_machine_ceo_tick(*, auto_kill: bool | None = None) -> dict[str, Any]:
    """Collect pulse; optionally auto-kill allowlisted junk when AUTO is on."""
    pulse = build_machine_pulse()
    autonomy_full = _autonomy_full()
    result: dict[str, Any] = {
        "ok": bool(pulse.get("ok")),
        "generated_at": utc_now_iso(),
        "autonomy_full": autonomy_full,
        "pulse": pulse,
        "kills": [],
        "skipped_kills": [],
        "spoken": str(pulse.get("spoken") or ""),
    }
    if not pulse.get("ok"):
        return result

    # Auto-kill only when Full autonomy AND caller asked for it (default: yes under AUTO).
    want_kill = autonomy_full if auto_kill is None else bool(auto_kill)
    do_kill = bool(want_kill and autonomy_full)
    if not do_kill:
        return result

    for item in pulse.get("recommendations") or []:
        if str(item.get("action") or "") != "kill":
            continue
        kill_result = kill_process(
            int(item["pid"]),
            require_auto_eligible=True,
            reason="machine_ceo_auto",
        )
        if kill_result.get("ok"):
            result["kills"].append(kill_result)
        else:
            result["skipped_kills"].append(kill_result)

    if result["kills"]:
        names = ", ".join(str(item.get("name") or item.get("pid")) for item in result["kills"][:3])
        result["spoken"] = (
            f"{pulse.get('spoken')} Reclaimed memory by stopping {names}."
        ).strip()
    return result


def kill_process(
    pid: int,
    *,
    require_auto_eligible: bool = False,
    reason: str = "operator_request",
    force: bool = False,
) -> dict[str, Any]:
    """Kill a process if policy allows. Never touches protected PIDs."""
    pulse = build_machine_pulse(process_limit=40)
    target = next(
        (item for item in pulse.get("processes") or [] if int(item.get("pid") or 0) == int(pid)),
        None,
    )
    if not target:
        # Still protect against killing unknown/protected via /proc
        try:
            os.kill(int(pid), 0)
        except OSError as exc:
            return {"ok": False, "pid": pid, "reason": f"not_found:{exc.__class__.__name__}"}
        return {
            "ok": False,
            "pid": pid,
            "reason": "not_in_pulse_snapshot",
        }

    if target.get("protected"):
        return {"ok": False, "pid": pid, "name": target.get("name"), "reason": "protected"}

    if require_auto_eligible and not target.get("auto_killable"):
        return {
            "ok": False,
            "pid": pid,
            "name": target.get("name"),
            "reason": "not_auto_killable",
        }

    if require_auto_eligible and not _autonomy_full():
        return {
            "ok": False,
            "pid": pid,
            "name": target.get("name"),
            "reason": "autonomy_not_full",
        }

    sig = signal.SIGKILL if force else signal.SIGTERM
    try:
        os.kill(int(pid), sig)
    except OSError as exc:
        logger.warning("machine ceo kill failed pid=%s: %s", pid, exc)
        return {
            "ok": False,
            "pid": pid,
            "name": target.get("name"),
            "reason": f"kill_failed:{exc.__class__.__name__}",
        }

    receipt = normalize_receipt(
        {
            "command_id": f"machine_kill_{pid}_{utc_now_iso()}",
            "action": "process.kill",
            "tier": "auto" if require_auto_eligible else "confirm",
            "status": "ok",
            "result_summary": f"Sent {sig.name} to {target.get('name')} ({pid})",
            "meta": {
                "pid": pid,
                "name": target.get("name"),
                "rss_mb": target.get("rss_mb"),
                "reason": reason,
                "signal": sig.name,
            },
        },
        device_id="local_control_plane",
    )
    store.insert_receipt(receipt)
    return {
        "ok": True,
        "pid": pid,
        "name": target.get("name"),
        "rss_mb": target.get("rss_mb"),
        "signal": sig.name,
        "reason": "killed",
        "receipt_id": receipt.get("receipt_id"),
    }
