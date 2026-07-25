"""Persist the bounded pre-unlock vault import without runtime imports."""

from __future__ import annotations

import json
from pathlib import Path

from app.vault.paths import vault_import_path


def load_vault_import() -> dict[str, str]:
    path = vault_import_path()
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    entries = payload.get("secrets")
    if not isinstance(entries, dict):
        return {}
    resolved: dict[str, str] = {}
    for key, value in entries.items():
        name = str(key).strip()
        text = str(value).strip()
        if name and text:
            resolved[name] = text
    return resolved


def save_vault_import(secrets: dict[str, str]) -> Path:
    path = vault_import_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": 1,
        "source": "axon-x-vault-import",
        "secrets": secrets,
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    path.chmod(0o600)
    return path
