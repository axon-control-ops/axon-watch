"""Skills catalog routes."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.skills_catalog import build_skills_snapshot
from app.workspace_project_bindings import WorkspaceBindingError

router = APIRouter()


@router.get("/api/skills")
def skills_index() -> dict[str, object]:
    try:
        return build_skills_snapshot()
    except WorkspaceBindingError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
