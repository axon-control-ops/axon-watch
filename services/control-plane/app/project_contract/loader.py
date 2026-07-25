"""Load and validate versioned project.axon.yaml contracts."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from app.project_contract.simple_yaml import SimpleYamlError, loads_simple_yaml

SUPPORTED_ADAPTERS = frozenset({"node_vue", "python_fastapi", "android_gradle"})
CERTIFICATION_LEVELS = frozenset(
    {"inspect_only", "build", "repair", "monitor_debug", "stage_recover", "bounded_production"}
)


class ProjectContractError(ValueError):
    """Invalid or unsupported project contract."""


def _as_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [str(item) for item in value]
    raise ProjectContractError(f"expected list or string, got {type(value).__name__}")


def _read_contract_mapping(path: Path) -> dict[str, Any]:
    try:
        raw = loads_simple_yaml(path.read_text(encoding="utf-8"))
    except SimpleYamlError as exc:
        raise ProjectContractError(str(exc)) from exc
    if not isinstance(raw, dict):
        raise ProjectContractError("project contract root must be a mapping")
    return raw


def load_project_contract(path: Path | str) -> dict[str, Any]:
    contract_path = Path(path)
    if not contract_path.is_file():
        raise ProjectContractError(f"project contract not found: {contract_path}")
    raw = _read_contract_mapping(contract_path)

    extends = raw.get("extends")
    if extends:
        parent_path = (contract_path.parent / str(extends)).resolve()
        if not parent_path.is_file():
            raise ProjectContractError(f"extended contract not found: {parent_path}")
        parent_raw = _read_contract_mapping(parent_path)
        merged: dict[str, Any] = {**parent_raw, **{k: v for k, v in raw.items() if k != "extends"}}
        if isinstance(parent_raw.get("commands"), dict) and isinstance(raw.get("commands"), dict):
            merged["commands"] = {**parent_raw["commands"], **raw["commands"]}
        if isinstance(parent_raw.get("verifier"), dict) and isinstance(raw.get("verifier"), dict):
            merged["verifier"] = {**parent_raw["verifier"], **raw["verifier"]}
        raw = merged

    return validate_project_contract(raw)


def validate_project_contract(raw: dict[str, Any]) -> dict[str, Any]:
    version = int(raw.get("version") or 0)
    if version != 1:
        raise ProjectContractError(f"unsupported contract version: {version}")

    project_id = str(raw.get("project_id") or "").strip()
    if not project_id:
        raise ProjectContractError("project_id is required")

    adapters = [str(item) for item in (raw.get("adapters") or [])]
    unsupported = [name for name in adapters if name not in SUPPORTED_ADAPTERS]
    certification = str(raw.get("certification_level") or "inspect_only").strip()
    if certification not in CERTIFICATION_LEVELS:
        raise ProjectContractError(f"unknown certification_level: {certification}")

    if unsupported and certification != "inspect_only":
        raise ProjectContractError(
            "unsupported adapters remain inspect-only: " + ", ".join(unsupported)
        )

    commands = raw.get("commands") or {}
    if not isinstance(commands, dict):
        raise ProjectContractError("commands must be a mapping")

    verifier = raw.get("verifier") or {}
    if not isinstance(verifier, dict):
        raise ProjectContractError("verifier must be a mapping")

    return {
        "version": version,
        "project_id": project_id,
        "display_name": str(raw.get("display_name") or project_id),
        "stack": str(raw.get("stack") or "unknown"),
        "certification_level": certification,
        "adapters": adapters,
        "unsupported_adapters": unsupported,
        "environment": raw.get("environment") or {},
        "commands": {str(k): _as_list(v) for k, v in commands.items()},
        "allowed_paths": _as_list(raw.get("allowed_paths")),
        "forbidden_path_globs": _as_list(raw.get("forbidden_path_globs")),
        "artifacts": _as_list(raw.get("artifacts")),
        "health_probes": _as_list(raw.get("health_probes")),
        "observability": raw.get("observability") or {},
        "deployment": raw.get("deployment") or {},
        "risk_tiers": raw.get("risk_tiers") or {},
        "approval_boundaries": _as_list(raw.get("approval_boundaries")),
        "verifier": {
            "identity": str(verifier.get("identity") or "verifier"),
            "immutable_to_implementer": bool(
                verifier.get("immutable_to_implementer", True)
            ),
            "required_checks": _as_list(verifier.get("required_checks")),
        },
        "inspect_only": certification == "inspect_only" or bool(unsupported),
    }


def resolve_default_contract(repo_root: Path | str) -> Path:
    root = Path(repo_root)
    root_contract = root / "project.axon.yaml"
    if root_contract.is_file():
        return root_contract
    bundled = root / "config" / "project-contracts" / "axon-watch.project.axon.yaml"
    if bundled.is_file():
        return bundled
    raise ProjectContractError("no project.axon.yaml found")
