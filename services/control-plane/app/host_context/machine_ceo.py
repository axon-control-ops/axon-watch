"""VAXON Machine CEO — act on host pulse under Full autonomy."""

from __future__ import annotations

import logging
import os
import signal
from typing import Any

from app.host_context.machine_pulse import (
    MEMORY_CEILING_PERCENT,
    build_machine_pulse,
)
from app.host_context.models import normalize_receipt, utc_now_iso
from app.host_context import store
from app.persistence import operator_presence_settings_store

logger = logging.getLogger(__name__)

_MAX_KILLS_PER_TICK = 6


def _autonomy_full() -> bool:
    settings = operator_presence_settings_store.load_settings()
    return str(settings.get("autonomy_mode") or "").strip().lower() == "full"


def run_machine_ceo_tick(*, auto_kill: bool | None = None) -> dict[str, Any]:
    """Collect pulse; reclaim allowlisted / pressure targets when AUTO is on."""
    pulse = build_machine_pulse(process_limit=16)
    autonomy_full = _autonomy_full()
    result: dict[str, Any] = {
        "ok": bool(pulse.get("ok")),
        "generated_at": utc_now_iso(),
        "autonomy_full": autonomy_full,
        "memory_ceiling_percent": MEMORY_CEILING_PERCENT,
        "memory_pressure": bool(pulse.get("memory_pressure")),
        "pulse": pulse,
        "kills": [],
        "skipped_kills": [],
        "spoken": str(pulse.get("spoken") or ""),
    }
    if not pulse.get("ok"):
        return result

    want_kill = autonomy_full if auto_kill is None else bool(auto_kill)
    do_kill = bool(want_kill and autonomy_full)
    if not do_kill:
        return result

    # First: pause optional services (idle CI runner / research containers).
    # Killing 6 jest PIDs is useless when 100+ runner workers hold ~5GB.
    if pulse.get("memory_pressure"):
        try:
            from app.host_context.machine_ceo_services import reclaim_optional_services

            result["service_reclaim"] = reclaim_optional_services()
        except Exception:  # noqa: BLE001
            logger.exception("optional service reclaim failed")
            result["service_reclaim"] = {"error": "service_reclaim_failed"}

    # Up to two passes while still over the ceiling (fresh pulse after first reclaim).
    for _pass in range(2):
        if _pass == 1:
            pulse = build_machine_pulse(process_limit=16)
            result["pulse"] = pulse
            result["memory_pressure"] = bool(pulse.get("memory_pressure"))
            if not pulse.get("memory_pressure"):
                break
        killable = [
            item
            for item in (pulse.get("recommendations") or [])
            if str(item.get("action") or "") == "kill"
        ][:_MAX_KILLS_PER_TICK]
        if not killable:
            break
        for item in killable:
            # Under pressure, SIGKILL — SIGTERM is too polite when RAM is critical.
            kill_result = kill_process(
                int(item["pid"]),
                require_auto_eligible=True,
                reason="machine_ceo_auto",
                pulse_snapshot=pulse,
                force=bool(pulse.get("memory_pressure")),
            )
            if kill_result.get("ok"):
                result["kills"].append(kill_result)
            else:
                result["skipped_kills"].append(kill_result)

    # #region agent log
    try:
        import json
        import time

        health = (
            (result.get("pulse") or {}).get("health")
            if isinstance((result.get("pulse") or {}).get("health"), dict)
            else {}
        )
        with open(
            "/home/edp/axon-nvme/repos/axon-watch/.cursor/debug-db8bb4.log",
            "a",
            encoding="utf-8",
        ) as _dbg:
            _dbg.write(
                json.dumps(
                    {
                        "sessionId": "db8bb4",
                        "runId": "machine-ceo",
                        "hypothesisId": "M1",
                        "location": "machine_ceo.py:run_machine_ceo_tick",
                        "message": "machine ceo reclaim tick",
                        "data": {
                            "mem_pct": health.get("memory_percent"),
                            "pressure": result.get("memory_pressure"),
                            "killed": len(result["kills"]),
                            "skipped": len(result["skipped_kills"]),
                            "names": [k.get("name") for k in result["kills"][:8]],
                        },
                        "timestamp": int(time.time() * 1000),
                    }
                )
                + "\n"
            )
    except Exception:
        pass
    # #endregion

    parts: list[str] = [str(pulse.get("spoken") or "").strip()]
    svc = result.get("service_reclaim") if isinstance(result.get("service_reclaim"), dict) else {}
    stopped_units = list(svc.get("stopped_units") or [])
    stopped_containers = list(svc.get("stopped_containers") or [])
    if stopped_units or stopped_containers:
        parts.append(
            "Paused "
            + ", ".join(stopped_units + stopped_containers)
            + "."
        )
    if result["kills"]:
        names = ", ".join(
            str(item.get("name") or item.get("pid")) for item in result["kills"][:3]
        )
        parts.append(f"Reclaimed memory by stopping {names}.")
    result["spoken"] = " ".join(p for p in parts if p).strip()
    return result


def kill_process(
    pid: int,
    *,
    require_auto_eligible: bool = False,
    reason: str = "operator_request",
    force: bool = False,
    pulse_snapshot: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Kill a process if policy allows. Never touches protected PIDs."""
    pulse = pulse_snapshot or build_machine_pulse(process_limit=40)
    target = next(
        (item for item in pulse.get("processes") or [] if int(item.get("pid") or 0) == int(pid)),
        None,
    )
    if not target:
        # Recommendations may include deeper scan rows not in the trimmed process list.
        for item in pulse.get("recommendations") or []:
            if int(item.get("pid") or 0) == int(pid) and str(item.get("action") or "") == "kill":
                # Re-scan full pulse for eligibility flags.
                deep = build_machine_pulse(process_limit=40)
                target = next(
                    (
                        row
                        for row in deep.get("processes") or []
                        if int(row.get("pid") or 0) == int(pid)
                    ),
                    None,
                )
                if target is None:
                    # Synthesize from recommendation under pressure reclaim.
                    target = {
                        "pid": pid,
                        "name": item.get("name"),
                        "rss_mb": item.get("rss_mb"),
                        "protected": False,
                        "auto_killable": True,
                    }
                break
    if not target:
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
