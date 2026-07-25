#!/usr/bin/env python3
"""Import Signal vault data into Axon-X monitor import or encrypted vault paths."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

WATCH_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(WATCH_ROOT / "services" / "axon-watch"))

from app.vault.credential_resolver import merge_vault_import  # noqa: E402
from app.vault.csv_import import parse_axon_vault_csv, parse_vault_export_text  # noqa: E402
from app.vault.snapshot import ALLOWED_IMPORT_KEYS  # noqa: E402

DEFAULT_KEYS = ALLOWED_IMPORT_KEYS


def _load_export(path: Path) -> dict[str, str]:
    return parse_vault_export_text(path.read_text(encoding="utf-8"), filename=path.name)


def _load_vault_rows(path: Path) -> list[dict[str, str]]:
    return parse_axon_vault_csv(path.read_text(encoding="utf-8"))


def _request_json(url: str, *, method: str = "GET", payload: dict[str, object] | None = None) -> dict:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    request = Request(
        url,
        data=data,
        method=method,
        headers={"Accept": "application/json", "Content-Type": "application/json"},
    )
    with urlopen(request, timeout=30) as response:
        parsed = json.loads(response.read().decode("utf-8"))
    if not isinstance(parsed, dict):
        raise RuntimeError(f"Unexpected response shape from {url}")
    return parsed


def _request_list(url: str) -> list[dict[str, object]]:
    request = Request(url, method="GET", headers={"Accept": "application/json"})
    with urlopen(request, timeout=30) as response:
        parsed = json.loads(response.read().decode("utf-8"))
    if not isinstance(parsed, list):
        raise RuntimeError(f"Unexpected list response from {url}")
    return [item for item in parsed if isinstance(item, dict)]


def _unlock_encrypted_vault(*, control_plane: str, master_password: str, totp_code: str) -> None:
    _request_json(
        f"{control_plane}/api/vault/unlock",
        method="POST",
        payload={
            "master_password": master_password,
            "totp_code": totp_code,
            "remember_me": True,
        },
    )


def _import_encrypted_rows(
    *,
    control_plane: str,
    rows: list[dict[str, str]],
    mode: str,
) -> tuple[int, int, int]:
    existing = _request_list(f"{control_plane}/api/vault/secrets")
    existing_by_name = {
        str(item.get("name") or "").strip(): item
        for item in existing
        if str(item.get("name") or "").strip()
    }

    added = 0
    updated = 0
    skipped = 0
    for row in rows:
        name = str(row.get("name") or "").strip()
        if not name:
            skipped += 1
            continue
        body = {
            "name": name,
            "category": str(row.get("category") or "general"),
            "username": str(row.get("username") or ""),
            "password": str(row.get("password") or ""),
            "url": str(row.get("url") or ""),
            "notes": str(row.get("notes") or ""),
        }
        existing_row = existing_by_name.get(name)
        if existing_row is None:
            _request_json(f"{control_plane}/api/vault/secrets", method="POST", payload=body)
            added += 1
            continue
        if mode == "merge":
            skipped += 1
            continue
        secret_id = int(existing_row["id"])
        _request_json(f"{control_plane}/api/vault/secrets/{secret_id}", method="PUT", payload=body)
        updated += 1
    return added, updated, skipped


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--from-export",
        type=Path,
        help="Axon vault CSV or JSON export (Axon-Signal / axon-local format)",
    )
    parser.add_argument(
        "--from-env",
        action="store_true",
        help="Copy DEFAULT_KEYS from the current process environment",
    )
    parser.add_argument(
        "--encrypted-vault",
        action="store_true",
        help="Import full secret rows into the unlocked encrypted vault via control-plane APIs",
    )
    parser.add_argument("--control-plane", default="http://127.0.0.1:8787")
    parser.add_argument("--master-password")
    parser.add_argument("--totp-code")
    parser.add_argument("--mode", choices=("merge", "replace"), default="merge")
    args = parser.parse_args()

    if args.encrypted_vault:
        if not args.from_export:
            parser.error("--encrypted-vault requires --from-export")
        if not args.master_password or not args.totp_code:
            parser.error("--encrypted-vault requires --master-password and --totp-code")
        export_path = args.from_export.expanduser().resolve()
        rows = _load_vault_rows(export_path)
        if not rows:
            print("No vault rows found to import.", file=sys.stderr)
            return 1
        base = args.control_plane.rstrip("/")
        try:
            _unlock_encrypted_vault(
                control_plane=base,
                master_password=args.master_password,
                totp_code=args.totp_code,
            )
            added, updated, skipped = _import_encrypted_rows(
                control_plane=base,
                rows=rows,
                mode=args.mode,
            )
        except HTTPError as exc:
            print(exc.read().decode("utf-8", errors="replace"), file=sys.stderr)
            return 1
        except URLError as exc:
            print(f"Control-plane unavailable: {exc}", file=sys.stderr)
            return 1
        print(
            f"Encrypted vault import complete: added={added} updated={updated} skipped={skipped}"
        )
        return 0

    secrets: dict[str, str] = {}
    if args.from_export:
        secrets.update(_load_export(args.from_export.expanduser().resolve()))
    if args.from_env or not secrets:
        for key in DEFAULT_KEYS:
            value = os.environ.get(key, "").strip()
            if value:
                secrets[key] = value

    if not secrets:
        print("No secrets found to import.", file=sys.stderr)
        return 1

    result = merge_vault_import(secrets, allowed_keys=ALLOWED_IMPORT_KEYS)
    print(f"Imported {result['count']} monitor key(s): {', '.join(result['imported_keys'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
