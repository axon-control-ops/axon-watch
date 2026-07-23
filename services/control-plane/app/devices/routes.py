"""HTTP routes for companion device enrollment / revocation."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query

from app.devices import store
from app.devices.models import DeviceEnrollRequest

router = APIRouter(tags=["devices"])


def _http_error(exc: store.DeviceEnrollmentError) -> HTTPException:
    detail = str(exc)
    lowered = detail.lower()
    if "not found" in lowered:
        return HTTPException(status_code=404, detail=detail)
    if "already exists" in lowered:
        return HTTPException(status_code=409, detail=detail)
    return HTTPException(status_code=400, detail=detail)


@router.post("/api/devices/enroll")
def enroll_device(body: DeviceEnrollRequest) -> dict[str, Any]:
    try:
        return store.enroll(
            label=body.label,
            platform=body.platform,
            capabilities=body.capabilities,
            device_id=body.device_id,
            meta=body.meta,
        )
    except store.DeviceEnrollmentError as exc:
        raise _http_error(exc) from exc


@router.post("/api/devices/{device_id}/revoke")
def revoke_device(device_id: str) -> dict[str, Any]:
    try:
        return store.revoke(device_id)
    except store.DeviceEnrollmentError as exc:
        raise _http_error(exc) from exc


@router.get("/api/devices")
def list_devices(
    status: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
) -> dict[str, Any]:
    items = store.list_devices(status=status, limit=limit)
    return {"items": items, "count": len(items)}


@router.get("/api/devices/{device_id}")
def get_device(device_id: str) -> dict[str, Any]:
    record = store.get_device(device_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"device not found: {device_id}")
    return record
