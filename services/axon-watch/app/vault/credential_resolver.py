"""Resolve monitor credentials from env, workspace dotenv, and Axon-X vault import."""

from __future__ import annotations

import os
import re
from pathlib import Path

from app.vault.import_contract import ALLOWED_IMPORT_KEYS
from app.vault.import_store import load_vault_import, save_vault_import
from app.vault.operations import vault_named_secrets_map, vault_runtime_env
from app.vault.paths import vault_import_path
from app.vault.session import VaultSession


def _service_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _repo_root() -> Path:
    return _service_root().parent.parent


def _state_dir() -> Path:
    configured = os.environ.get("AXON_WATCH_STATE_DIR", ".local/state").strip()
    path = Path(configured).expanduser()
    if not path.is_absolute():
        path = (_repo_root() / path).resolve()
    return path

def parse_dotenv_file(path: Path) -> dict[str, str]:
    if not path.is_file():
        return {}
    resolved: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            resolved[key] = value
    return resolved


def merge_monitor_env(*, project_root: Path | None = None) -> dict[str, str]:
    env = {key: value for key, value in os.environ.items() if value is not None}

    if VaultSession.is_unlocked():
        env.update(vault_named_secrets_map(ALLOWED_IMPORT_KEYS))
        env.update(vault_runtime_env())
    else:
        env.update(load_vault_import())
    if project_root is not None and project_root.is_dir():
        for name in (".env", ".env.local", ".env.production"):
            env.update(parse_dotenv_file(project_root / name))
    return env


def list_available_credential_keys(env: dict[str, str]) -> list[str]:
    interesting = (
        "SENTRY_AUTH_TOKEN",
        "SENTRY_API_TOKEN",
        "POSTHOG_PERSONAL_API_KEY",
        "DASHPRO_POSTHOG_PROJECT_ID",
        "EXPO_PUBLIC_POSTHOG_KEY",
        "EXPO_PUBLIC_POSTHOG_HOST",
        "EXPO_PUBLIC_SENTRY_DSN",
        "CURSOR_API_KEY",
        "CODEX_API_KEY",
        "OPENAI_API_KEY",
    )
    return [name for name in interesting if str(env.get(name, "")).strip()]


def merge_vault_import(
    secrets: dict[str, str],
    *,
    allowed_keys: tuple[str, ...] | None = None,
) -> dict[str, object]:
    allowed = set(allowed_keys or ())
    filtered: dict[str, str] = {}
    for key, value in secrets.items():
        name = str(key).strip()
        text = str(value).strip()
        if not name or not text:
            continue
        if allowed and name not in allowed:
            continue
        filtered[name] = text

    if not filtered:
        return {"imported_keys": [], "count": 0}

    merged = load_vault_import()
    merged.update(filtered)
    save_vault_import(merged)
    return {
        "imported_keys": sorted(filtered.keys()),
        "count": len(filtered),
    }


def vault_status(*, project_root: Path | None = None) -> dict[str, object]:
    env = merge_monitor_env(project_root=project_root)
    import_path = vault_import_path()
    imported = load_vault_import()
    return {
        "import_file_present": import_path.is_file(),
        "import_file": str(import_path),
        "imported_keys": sorted(imported.keys()),
        "imported_key_count": len(imported),
        "available_keys": list_available_credential_keys(env),
        "sources": [
            "process_env",
            *(["vault_import"] if import_path.is_file() else []),
            *(["workspace_dotenv"] if project_root is not None else []),
        ],
    }
