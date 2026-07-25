#!/usr/bin/env python3
"""Migrate Axon-Signal vault export into Axon-X encrypted vault (operator-run)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

REPO_ROOT = Path(__file__).resolve().parents[2]
WATCH_ROOT = REPO_ROOT / "services" / "axon-watch"
sys.path.insert(0, str(WATCH_ROOT))

from app.vault.csv_import import parse_axon_vault_csv  # noqa: E402


def _post_json(url: str, payload: dict) -> dict:
    data = json.dumps(payload).encode("utf-8")
    request = Request(
        url,
        data=data,
        method="POST",
        headers={"Accept": "application/json", "Content-Type": "application/json"},
    )
    with urlopen(request, timeout=30) as response:
        body = response.read().decode("utf-8")
    parsed = json.loads(body)
    if not isinstance(parsed, dict):
        raise RuntimeError("Unexpected response shape")
    return parsed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--control-plane", default="http://127.0.0.1:8787")
    parser.add_argument("--export", type=Path, required=True, help="Signal vault CSV export")
    parser.add_argument("--master-password", required=True)
    parser.add_argument("--totp-code", required=True)
    args = parser.parse_args()

    base = args.control_plane.rstrip("/")
    export_path = args.export.expanduser().resolve()
    if not export_path.is_file():
        print(f"Export not found: {export_path}", file=sys.stderr)
        return 1

    try:
        unlock = _post_json(
            f"{base}/api/vault/unlock",
            {
                "master_password": args.master_password,
                "totp_code": args.totp_code,
                "remember_me": True,
            },
        )
    except HTTPError as exc:
        print(exc.read().decode("utf-8", errors="replace"), file=sys.stderr)
        return 1
    except URLError as exc:
        print(f"Control-plane unavailable: {exc}", file=sys.stderr)
        return 1

    rows = parse_axon_vault_csv(export_path.read_text(encoding="utf-8"))
    added = 0
    for row in rows:
        name = row.get("name", "").strip()
        password = row.get("password", "").strip()
        if not name:
            continue
        _post_json(
            f"{base}/api/vault/secrets",
            {
                "name": name,
                "category": row.get("category") or "general",
                "username": row.get("username") or "",
                "password": password,
                "url": row.get("url") or "",
                "notes": row.get("notes") or "",
            },
        )
        added += 1

    print(json.dumps({"unlocked": unlock.get("unlocked"), "imported_secrets": added}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
