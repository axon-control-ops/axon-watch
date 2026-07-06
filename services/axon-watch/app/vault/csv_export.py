"""CSV export helpers for vault parity."""

from __future__ import annotations

import csv
import io
import re
import secrets
from datetime import datetime, timezone
from typing import Any, Literal

from app.vault.backup import normalize_secret_row

CsvFormat = Literal["axon", "bitwarden"]

AXON_CSV_COLUMNS = ("name", "category", "username", "password", "url", "notes")
BITWARDEN_CSV_COLUMNS = (
    "folder",
    "favorite",
    "type",
    "name",
    "notes",
    "fields",
    "reprompt",
    "login_uri",
    "login_username",
    "login_password",
    "login_totp",
)


def _sorted_secrets(secrets: list[dict[str, Any]]) -> list[dict[str, str]]:
    cleaned = [normalize_secret_row(item) for item in secrets if str(item.get("name") or "").strip()]
    cleaned.sort(key=lambda item: item["name"].lower())
    return cleaned


def _bitwarden_login_uri(url: str) -> str:
    value = str(url or "").strip()
    if not value:
        return ""
    if re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", value):
        return value
    if "." in value:
        return f"https://{value.lstrip('/')}"
    return value


def _bitwarden_item_type(row: dict[str, str]) -> str:
    if row.get("password") or row.get("username"):
        return "login"
    return "note"


def _bitwarden_folder(category: str) -> str:
    value = str(category or "").strip()
    if not value or value.lower() == "general":
        return ""
    return value


def secrets_to_axon_csv(secrets: list[dict[str, Any]]) -> str:
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=list(AXON_CSV_COLUMNS), lineterminator="\n")
    writer.writeheader()
    for row in _sorted_secrets(secrets):
        writer.writerow(row)
    return buffer.getvalue()


def secrets_to_bitwarden_csv(secrets: list[dict[str, Any]]) -> str:
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=list(BITWARDEN_CSV_COLUMNS), lineterminator="\n")
    writer.writeheader()
    for row in _sorted_secrets(secrets):
        writer.writerow(
            {
                "folder": _bitwarden_folder(row["category"]),
                "favorite": "0",
                "type": _bitwarden_item_type(row),
                "name": row["name"],
                "notes": row["notes"],
                "fields": "",
                "reprompt": "0",
                "login_uri": _bitwarden_login_uri(row["url"]),
                "login_username": row["username"],
                "login_password": row["password"],
                "login_totp": "",
            }
        )
    return buffer.getvalue()


def suggested_csv_filename(csv_format: CsvFormat = "axon") -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    token = secrets.token_hex(3)
    suffix = "bitwarden" if csv_format == "bitwarden" else "axon"
    return f"axon-vault-{suffix}-{stamp}-{token}.csv"


def collect_decrypted_secrets(list_fn, get_fn, key: bytes) -> list[dict[str, Any]]:
    metadata = list_fn()
    secrets: list[dict[str, Any]] = []
    for row in metadata:
        secret = get_fn(int(row["id"]), key)
        if secret:
            secrets.append(secret)
    return secrets
