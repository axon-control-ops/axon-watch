"""Load configured watch connector definitions."""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path


class ConnectorConfigError(ValueError):
    pass


@dataclass(frozen=True)
class WatchConnectorDefinition:
    connector_id: str
    display_name: str
    health_url: str
    required: bool
    workspace_id: str


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def default_connectors_file() -> Path:
    configured = os.environ.get("AXON_WATCH_CONNECTORS_FILE", "").strip()
    if configured:
        path = Path(configured).expanduser()
        if not path.is_absolute():
            path = (_repo_root() / path).resolve()
        return path
    return (_repo_root() / "config" / "watch-connectors.json").resolve()


_UNRESOLVED_ENV_PATTERN = re.compile(r"\$\{[^}]+\}|\$[A-Za-z_][A-Za-z0-9_]*")


def _bootstrap_connector_env() -> None:
    """Mirror run-service.sh localhost defaults so connector probes work without deployment.env."""
    os.environ.setdefault("AXON_WATCH_CONSOLE_WEB_PORT", "4173")
    os.environ.setdefault("AXON_WATCH_CONTROL_PLANE_PORT", "8787")
    os.environ.setdefault("AXON_WATCH_WATCH_SERVICE_PORT", "8788")

    console_port = os.environ["AXON_WATCH_CONSOLE_WEB_PORT"]
    control_plane_port = os.environ["AXON_WATCH_CONTROL_PLANE_PORT"]
    watch_port = os.environ["AXON_WATCH_WATCH_SERVICE_PORT"]

    os.environ.setdefault(
        "AXON_WATCH_PUBLIC_BASE_URL",
        f"http://127.0.0.1:{console_port}",
    )
    os.environ.setdefault(
        "AXON_WATCH_CONTROL_PLANE_BASE_URL",
        f"http://127.0.0.1:{control_plane_port}",
    )
    os.environ.setdefault(
        "AXON_WATCH_WATCH_SERVICE_BASE_URL",
        f"http://127.0.0.1:{watch_port}",
    )


def _resolve_health_url(raw_url: str) -> str:
    _bootstrap_connector_env()
    text = os.path.expandvars(raw_url.strip())
    if not text:
        raise ConnectorConfigError("health_url is required")
    if _UNRESOLVED_ENV_PATTERN.search(text):
        raise ConnectorConfigError(
            f"health_url has unresolved environment placeholders: {text}"
        )
    return text


def load_watch_connector_definitions(
    connectors_file: Path | None = None,
) -> dict[str, WatchConnectorDefinition]:
    path = connectors_file or default_connectors_file()
    if not path.is_file():
        return {}

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ConnectorConfigError(f"unable to read connectors file: {path}") from exc

    entries = payload.get("connectors")
    if not isinstance(entries, dict):
        raise ConnectorConfigError("connectors file must contain a connectors object")

    definitions: dict[str, WatchConnectorDefinition] = {}
    for connector_id, entry in entries.items():
        normalized_id = str(connector_id).strip()
        if not normalized_id:
            continue
        if not isinstance(entry, dict):
            raise ConnectorConfigError(f"connector {normalized_id} must be an object")

        health_url = _resolve_health_url(str(entry.get("health_url", "")))
        display_name = str(entry.get("display_name", "")).strip() or normalized_id
        workspace_id = str(entry.get("workspace_id", "workspace_axon_watch")).strip()
        required = bool(entry.get("required", False))

        definitions[normalized_id] = WatchConnectorDefinition(
            connector_id=normalized_id,
            display_name=display_name,
            health_url=health_url,
            required=required,
            workspace_id=workspace_id or "workspace_axon_watch",
        )

    return definitions
