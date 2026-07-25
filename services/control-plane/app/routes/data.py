"""Data snapshot and export routes."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from app.data.routes import get_data_export, get_data_snapshot

router = APIRouter()


@router.get("/api/data/snapshot")
def data_snapshot_route(limit: int = 50) -> dict[str, object]:
    try:
        return get_data_snapshot(limit=limit)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/api/data/export")
def data_export_route(limit: int = 50) -> JSONResponse:
    try:
        payload = get_data_export(limit=limit)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return JSONResponse(
        content=payload,
        headers={
            "Content-Disposition": 'attachment; filename="axon-operator-data-export.json"',
        },
    )
