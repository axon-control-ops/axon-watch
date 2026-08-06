"""VAXON fleet self-heal — repair-worker outcome callback."""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from app.fleet_self_heal.report import mark_repair_outcome, spoken_report_line
from app.fleet_self_heal import store

logger = logging.getLogger(__name__)

router = APIRouter(tags=["fleet-self-heal"])


@router.post("/api/fleet-self-heal/report-outcome")
def fleet_self_heal_report_outcome(body: dict[str, object]) -> dict[str, object]:
    """Repair-worker callback path to mark a fleet fingerprint fixed or still open."""
    fingerprint = str(body.get("fingerprint") or "").strip()
    if not fingerprint:
        raise HTTPException(status_code=400, detail="fingerprint is required")
    success = bool(body.get("success"))
    commit_ref = str(body.get("commit_ref") or "").strip()
    detail = str(body.get("detail") or "").strip()

    event = store.get_event(fingerprint)
    subsystem = str((event or {}).get("subsystem") or "unknown")

    signal = mark_repair_outcome(
        fingerprint=fingerprint, success=success, commit_ref=commit_ref, detail=detail,
    )
    spoken = spoken_report_line(success=success, subsystem=subsystem, detail=detail or commit_ref)
    logger.info(
        "fleet_self_heal_report_outcome fingerprint=%s success=%s status=%s",
        fingerprint, success, signal.get("status"),
    )
    return {
        "ok": True,
        "signal_id": signal.get("signal_id"),
        "spoken": spoken,
        "status": signal.get("status"),
    }
