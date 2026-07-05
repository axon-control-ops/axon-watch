#!/usr/bin/env python3
"""Import named monitor secrets into Axon-X vault-import.json from env or Signal export."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

WATCH_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(WATCH_ROOT / "services" / "axon-watch"))

from app.vault.credential_resolver import save_vault_import  # noqa: E402

DEFAULT_KEYS = (
    "SENTRY_AUTH_TOKEN",
    "SENTRY_API_TOKEN",
    "POSTHOG_PERSONAL_API_KEY",
    "DASHPRO_POSTHOG_PROJECT_ID",
    "EXPO_PUBLIC_POSTHOG_KEY",
    "EXPO_PUBLIC_POSTHOG_HOST",
    "EXPO_PUBLIC_SENTRY_DSN",
    "SENTRY_ORG_SLUG",
    "SENTRY_PROJECT_SLUG",
)


def _load_export(path: Path) -> dict[str, str]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, dict) and isinstance(payload.get("secrets"), dict):
        entries = payload["secrets"]
    elif isinstance(payload, dict):
        entries = payload
    else:
        raise ValueError("export file must be a JSON object or {secrets: {...}}")
    resolved: dict[str, str] = {}
    for key, value in entries.items():
        name = str(key).strip()
        text = str(value).strip()
        if name and text:
            resolved[name] = text
    return resolved


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--from-export",
        type=Path,
        help="JSON export from Axon-Signal vault (object or {secrets: {...}})",
    )
    parser.add_argument(
        "--from-env",
        action="store_true",
        help="Copy DEFAULT_KEYS from the current process environment",
    )
    args = parser.parse_args()

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

    path = save_vault_import(secrets)
    print(f"Imported {len(secrets)} secret(s) into {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
