"""Operator inbox signal acknowledgement via watch commands."""

from __future__ import annotations

from app.adapters.watch_client import post_watch_command


def acknowledge_inbox_signals(
    signal_ids: list[str],
    *,
    requested_by: str = "operator",
) -> dict[str, object]:
    normalized = [signal_id.strip() for signal_id in signal_ids if signal_id.strip()]
    if not normalized:
        return {"accepted": True, "acknowledged": [], "count": 0}

    payload = post_watch_command(
        {
            "command_type": "acknowledge_signal",
            "target_type": "signal",
            "requested_by": requested_by,
            "payload": {"signal_ids": normalized},
        }
    )
    if payload is None:
        return {"accepted": False, "acknowledged": [], "count": 0, "error": "watch unavailable"}

    receipt = payload.get("receipt", {})
    result = receipt.get("result", {}) if isinstance(receipt, dict) else {}
    acknowledged = result.get("acknowledged", []) if isinstance(result, dict) else []
    if not isinstance(acknowledged, list):
        acknowledged = []

    return {
        "accepted": bool(payload.get("accepted", False)),
        "acknowledged": acknowledged,
        "count": len(acknowledged),
        "command_id": payload.get("command_id", ""),
        "status": payload.get("status", ""),
    }
