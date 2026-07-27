"""Operator inbox signal acknowledgement (watch + Gate 9 CI store)."""

from __future__ import annotations

from app.adapters.watch_client import post_watch_command, reset_watch_inbox_cache


def acknowledge_inbox_signals(
    signal_ids: list[str],
    *,
    requested_by: str = "operator",
) -> dict[str, object]:
    normalized = [signal_id.strip() for signal_id in signal_ids if signal_id.strip()]
    if not normalized:
        return {"accepted": True, "acknowledged": [], "count": 0}

    acknowledged: list[str] = []

    # Gate 9 CI signals live in control-plane SQLite — watch ack alone cannot clear them.
    try:
        from app.ci_remediation import store as ci_store

        ci_resolved = ci_store.resolve_signals(
            normalized,
            reason=f"acknowledged_by_{requested_by or 'operator'}",
        )
        for row in ci_resolved:
            signal_id = str(row.get("signal_id") or "").strip()
            if signal_id:
                acknowledged.append(signal_id)
            dedupe = str(row.get("dedupe_key") or "").strip()
            if dedupe:
                ci_store.set_event_status(dedupe, "resolved")
    except Exception:  # noqa: BLE001 — still attempt watch ack
        pass

    remaining = [signal_id for signal_id in normalized if signal_id not in set(acknowledged)]
    payload: dict[str, object] | None = None
    if remaining:
        payload = post_watch_command(
            {
                "command_type": "acknowledge_signal",
                "target_type": "signal",
                "requested_by": requested_by,
                "payload": {"signal_ids": remaining},
            }
        )
        if payload is not None:
            receipt = payload.get("receipt", {})
            result = receipt.get("result", {}) if isinstance(receipt, dict) else {}
            watch_acked = result.get("acknowledged", []) if isinstance(result, dict) else []
            if isinstance(watch_acked, list):
                for item in watch_acked:
                    text = str(item or "").strip()
                    if text and text not in acknowledged:
                        acknowledged.append(text)

    accepted = bool(acknowledged) or (
        payload is not None and bool(payload.get("accepted", False))
    )
    if accepted:
        reset_watch_inbox_cache()

    if not remaining and acknowledged:
        return {
            "accepted": True,
            "acknowledged": acknowledged,
            "count": len(acknowledged),
            "command_id": "",
            "status": "resolved",
        }

    if payload is None and not acknowledged:
        return {"accepted": False, "acknowledged": [], "count": 0, "error": "watch unavailable"}

    return {
        "accepted": accepted,
        "acknowledged": acknowledged,
        "count": len(acknowledged),
        "command_id": str((payload or {}).get("command_id", "")),
        "status": str((payload or {}).get("status", "")),
    }
