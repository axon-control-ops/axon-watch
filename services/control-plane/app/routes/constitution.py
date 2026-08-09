"""Read APIs for the AXON-X Engineering Constitution registries."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.persistence import constitution_registry_store as registry
from app.persistence import evidence_ref_adapters

router = APIRouter(tags=["constitution"])


class MissionCreateRequest(BaseModel):
    title: str = Field(min_length=1)
    workspace_id: str = ""
    description: str = ""
    risk: str = "normal"
    lead_plan_id: str | None = None
    success_criteria: list[str] = Field(default_factory=list)


class MissionCheckpointRequest(BaseModel):
    checkpoint: dict[str, Any] = Field(default_factory=dict)


class CapabilityUpsertRequest(BaseModel):
    capability_id: str | None = None
    name: str = Field(min_length=1)
    description: str = ""
    status: str = "active"
    owner_role: str = ""
    route_paths: list[str] = Field(default_factory=list)
    adr_ids: list[str] = Field(default_factory=list)
    success_criteria: list[str] = Field(default_factory=list)
    version: str = "0.1.0"


class AdrUpsertRequest(BaseModel):
    number: int = Field(ge=1)
    title: str = Field(min_length=1)
    status: str = "proposed"
    doc_path: str = ""
    summary: str = ""
    capability_ids: list[str] = Field(default_factory=list)


class DebtCreateRequest(BaseModel):
    title: str = Field(min_length=1)
    description: str = ""
    severity: str = "low"
    area: str = ""
    evidence_ids: list[str] = Field(default_factory=list)
    adr_id: str | None = None


class HealthSnapshotRequest(BaseModel):
    scope: str = "platform"
    status: str = Field(min_length=1)
    signals: dict[str, Any] = Field(default_factory=dict)
    source: str = ""


@router.get("/api/operator/constitution")
def constitution_overview() -> dict[str, Any]:
    return {
        "status": "available",
        "registries": registry.registry_counts(),
        "source_of_truth": "AXON-X Engineering Constitution",
    }


@router.get("/api/operator/constitution/evidence")
def constitution_evidence(
    mission_id: str = "",
    run_id: str = "",
    task_id: str = "",
    source_table: str = "",
    limit: int = Query(default=50, ge=1, le=200),
) -> dict[str, Any]:
    items = registry.list_evidence(
        mission_id=mission_id or None,
        run_id=run_id or None,
        task_id=task_id or None,
        source_table=source_table or None,
        limit=limit,
    )
    return {"items": items, "count": len(items)}


@router.post("/api/operator/constitution/evidence/backfill")
def constitution_evidence_backfill(
    limit_per_source: int = Query(default=200, ge=1, le=500),
) -> dict[str, Any]:
    results = evidence_ref_adapters.backfill_all(limit_per_source=limit_per_source)
    return {"results": results, "indexed": sum(v for v in results.values() if isinstance(v, int))}


@router.get("/api/operator/constitution/missions")
def constitution_missions(
    workspace_id: str = "",
    status: str = "",
    limit: int = Query(default=50, ge=1, le=200),
) -> dict[str, Any]:
    items = registry.list_missions(
        workspace_id=workspace_id or None,
        status=status or None,
        limit=limit,
    )
    return {"items": items, "count": len(items)}


@router.post("/api/operator/constitution/missions")
def constitution_mission_create(body: MissionCreateRequest) -> dict[str, Any]:
    try:
        return registry.create_mission(
            title=body.title,
            workspace_id=body.workspace_id,
            description=body.description,
            risk=body.risk,
            lead_plan_id=body.lead_plan_id,
            success_criteria=body.success_criteria,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/api/operator/constitution/missions/{mission_id}")
def constitution_mission_get(mission_id: str) -> dict[str, Any]:
    mission = registry.get_mission(mission_id)
    if mission is None:
        raise HTTPException(status_code=404, detail=f"mission not found: {mission_id}")
    return mission


@router.post("/api/operator/constitution/missions/{mission_id}/checkpoint")
def constitution_mission_checkpoint(
    mission_id: str,
    body: MissionCheckpointRequest,
) -> dict[str, Any]:
    try:
        return registry.update_mission_checkpoint(mission_id, body.checkpoint)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/api/operator/constitution/decisions")
def constitution_decisions(
    mission_id: str = "",
    task_id: str = "",
    run_id: str = "",
    limit: int = Query(default=50, ge=1, le=200),
) -> dict[str, Any]:
    items = registry.list_decisions(
        mission_id=mission_id or None,
        task_id=task_id or None,
        run_id=run_id or None,
        limit=limit,
    )
    return {"items": items, "count": len(items)}


@router.get("/api/operator/constitution/capabilities")
def constitution_capabilities(
    status: str = "",
    limit: int = Query(default=200, ge=1, le=500),
) -> dict[str, Any]:
    items = registry.list_capabilities(status=status or None, limit=limit)
    return {"items": items, "count": len(items)}


@router.post("/api/operator/constitution/capabilities")
def constitution_capability_upsert(body: CapabilityUpsertRequest) -> dict[str, Any]:
    try:
        return registry.upsert_capability(
            capability_id=body.capability_id,
            name=body.name,
            description=body.description,
            status=body.status,
            owner_role=body.owner_role,
            route_paths=body.route_paths,
            adr_ids=body.adr_ids,
            success_criteria=body.success_criteria,
            version=body.version,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/api/operator/constitution/seed")
def constitution_seed() -> dict[str, Any]:
    from app.constitution_seed import seed_constitution_registries

    results = seed_constitution_registries()
    return {"results": results, "seeded": sum(results.values())}


@router.get("/api/operator/constitution/adrs")
def constitution_adrs(
    status: str = "",
    limit: int = Query(default=200, ge=1, le=500),
) -> dict[str, Any]:
    items = registry.list_adrs(status=status or None, limit=limit)
    return {"items": items, "count": len(items)}


@router.post("/api/operator/constitution/adrs")
def constitution_adr_upsert(body: AdrUpsertRequest) -> dict[str, Any]:
    try:
        return registry.upsert_adr(
            number=body.number,
            title=body.title,
            status=body.status,
            doc_path=body.doc_path,
            summary=body.summary,
            capability_ids=body.capability_ids,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/api/operator/constitution/debt")
def constitution_debt(
    status: str = "open",
    limit: int = Query(default=100, ge=1, le=500),
) -> dict[str, Any]:
    items = registry.list_debt(status=status or None, limit=limit)
    return {"items": items, "count": len(items)}


@router.post("/api/operator/constitution/debt")
def constitution_debt_create(body: DebtCreateRequest) -> dict[str, Any]:
    try:
        return registry.record_debt(
            title=body.title,
            description=body.description,
            severity=body.severity,
            area=body.area,
            evidence_ids=body.evidence_ids,
            adr_id=body.adr_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/api/operator/constitution/health")
def constitution_health_snapshots(
    scope: str = "platform",
    limit: int = Query(default=50, ge=1, le=200),
) -> dict[str, Any]:
    items = registry.list_health_snapshots(scope=scope, limit=limit)
    return {"items": items, "count": len(items)}


@router.post("/api/operator/constitution/health")
def constitution_health_snapshot_create(body: HealthSnapshotRequest) -> dict[str, Any]:
    try:
        return registry.record_health_snapshot(
            scope=body.scope,
            status=body.status,
            signals=body.signals,
            source=body.source,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/api/operator/constitution/health/capture-runtime-summary")
def constitution_health_capture_runtime_summary() -> dict[str, Any]:
    from app.constitution_health import record_runtime_summary_health_snapshot
    from app.runtime_summary_assembler import assemble_runtime_summary

    runtime_summary = assemble_runtime_summary(light=True)
    snapshot = record_runtime_summary_health_snapshot(
        runtime_summary,
        source="runtime_summary_light",
    )
    return {"snapshot": snapshot, "runtime_generated_at": runtime_summary.get("generated_at")}
