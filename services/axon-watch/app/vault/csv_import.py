"""Parse Axon-Signal / Axon-local vault CSV exports for monitor import."""

from __future__ import annotations

import csv
import io
import json
import re

from app.vault.snapshot import ALLOWED_IMPORT_KEYS

AXON_CSV_COLUMNS = ("name", "category", "username", "password", "url", "notes")

_HEADER_ALIASES = {
    "name": "name",
    "category": "category",
    "username": "username",
    "user": "username",
    "password": "password",
    "pass": "password",
    "url": "url",
    "uri": "url",
    "login_uri": "url",
    "notes": "notes",
    "note": "notes",
    "login_username": "username",
    "login_password": "password",
}

_MONITOR_KEY_ALIASES = {
    "DASHPRO_SENTRY_ORG_SLUG": "SENTRY_ORG_SLUG",
    "DASHPRO_SENTRY_PROJECT_SLUG": "SENTRY_PROJECT_SLUG",
}


def looks_like_axon_vault_csv(raw_text: str) -> bool:
    first_line = str(raw_text or "").splitlines()[0] if str(raw_text or "").strip() else ""
    if not first_line or "," not in first_line:
        return False
    headers = {cell.strip().lower() for cell in first_line.split(",")}
    return "name" in headers and (
        "password" in headers or "category" in headers or "login_password" in headers
    )


def _map_header_field(raw_header: str) -> str | None:
    key = str(raw_header or "").strip().lower()
    if not key:
        return None
    return _HEADER_ALIASES.get(key)


def _normalize_row(payload: dict[str, str]) -> dict[str, str]:
    return {
        field: str(payload.get(field) or "").strip()
        for field in AXON_CSV_COLUMNS
    }


def _row_monitor_value(row: dict[str, str]) -> str:
    password = row.get("password", "").strip()
    if password:
        return password
    return row.get("username", "").strip()


def parse_axon_vault_csv(raw_text: str) -> list[dict[str, str]]:
    text = str(raw_text or "")
    if not text.strip():
        return []
    reader = csv.DictReader(io.StringIO(text, newline=""))
    if not reader.fieldnames:
        return []
    column_map: dict[str, str] = {}
    for header in reader.fieldnames:
        mapped = _map_header_field(header)
        if mapped and mapped not in column_map:
            column_map[mapped] = header
    if "name" not in column_map:
        return []

    rows: list[dict[str, str]] = []
    for raw_row in reader:
        if not raw_row:
            continue
        payload: dict[str, str] = {}
        for field in AXON_CSV_COLUMNS:
            source_header = column_map.get(field)
            payload[field] = raw_row.get(source_header, "") if source_header else ""
        normalized = _normalize_row(payload)
        if normalized["name"]:
            rows.append(normalized)
    return rows


def monitor_secrets_from_axon_rows(rows: list[dict[str, str]]) -> dict[str, str]:
    allowed = set(ALLOWED_IMPORT_KEYS)
    secrets: dict[str, str] = {}
    for row in rows:
        raw_name = row["name"]
        target_name = _MONITOR_KEY_ALIASES.get(raw_name, raw_name)
        if target_name not in allowed:
            continue
        value = _row_monitor_value(row)
        if value:
            secrets[target_name] = value
    return secrets


def parse_vault_export_text(raw_text: str, *, filename: str = "") -> dict[str, str]:
    text = str(raw_text or "").strip()
    if not text:
        return {}

    lower_name = filename.lower()
    if lower_name.endswith(".json") or text.startswith("{"):
        payload = json.loads(text)
        entries = payload.get("secrets") if isinstance(payload, dict) else None
        if not isinstance(entries, dict) and isinstance(payload, dict):
            entries = payload
        if not isinstance(entries, dict):
            return {}
        return {
            str(key).strip(): str(value).strip()
            for key, value in entries.items()
            if str(key).strip() and str(value).strip()
        }

    if looks_like_axon_vault_csv(text) or lower_name.endswith(".csv"):
        rows = parse_axon_vault_csv(text)
        if rows:
            return monitor_secrets_from_axon_rows(rows)

    secrets: dict[str, str] = {}
    for line in text.splitlines():
        trimmed = line.strip()
        if not trimmed or trimmed.startswith("#") or "=" not in trimmed:
            continue
        key, _, value = trimmed.partition("=")
        name = key.strip()
        text_value = value.strip().strip('"').strip("'")
        if name and text_value:
            secrets[name] = text_value
    return secrets
