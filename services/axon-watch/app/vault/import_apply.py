"""Apply decrypted vault backups into the live encrypted vault."""

from __future__ import annotations

from typing import Any, Literal

ImportMode = Literal["merge", "replace"]


def import_vault_secrets(
    *,
    list_by_name,
    add_secret,
    update_secret,
    vault_key: bytes,
    secrets: list[dict[str, Any]],
    mode: ImportMode = "merge",
) -> dict[str, int]:
    added = 0
    updated = 0
    skipped = 0
    for raw in secrets:
        name = str(raw.get("name") or "").strip()
        if not name:
            skipped += 1
            continue
        row = list_by_name(name)
        exists = row is not None
        if exists and mode == "merge":
            skipped += 1
            continue
        category = str(raw.get("category") or "general").strip() or "general"
        username = str(raw.get("username") or "").strip()
        password = str(raw.get("password") or "").strip()
        url = str(raw.get("url") or "").strip()
        notes = str(raw.get("notes") or "").strip()
        if exists and mode == "replace":
            secret_id = int(row["id"])
            update_secret(vault_key, secret_id, name, category, username, password, url, notes)
            updated += 1
            continue
        add_secret(vault_key, name, category, username, password, url, notes)
        added += 1
    return {"added": added, "updated": updated, "skipped": skipped}
