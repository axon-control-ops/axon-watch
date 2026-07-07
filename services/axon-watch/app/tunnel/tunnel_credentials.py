"""Cloudflare tunnel credential resolution for Axon-X remote control."""

from __future__ import annotations

import os
import shlex
from pathlib import Path


def legacy_tunnel_env_file(*, home_path: Path | None = None) -> Path:
    root = home_path or Path.home()
    return root / ".devbrain" / "axon-tunnel.env"


def default_user_service_file(*, home_path: Path | None = None) -> Path:
    root = home_path or Path.home()
    return root / ".config" / "systemd" / "user" / "axon-tunnel.service"


def _clean_token(value: str | None) -> str:
    return str(value or "").strip().strip('"').strip("'")


def _is_vault_reference(value: str | None) -> bool:
    return _clean_token(value).startswith("vault:")


def read_tunnel_token_from_env_file(path: Path) -> str:
    try:
        for raw_line in path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            key, sep, value = line.partition("=")
            if sep and key.strip() == "TUNNEL_TOKEN":
                token = _clean_token(value)
                if token:
                    return token
    except OSError:
        pass
    return ""


def read_tunnel_token_from_service_file(path: Path) -> str:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return ""

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue

        if line.startswith("Environment="):
            payload = _clean_token(line.split("=", 1)[1])
            if payload.startswith("TUNNEL_TOKEN="):
                token = _clean_token(payload.split("=", 1)[1])
                if token and not _is_vault_reference(token):
                    return token
            if payload.startswith("AXON_CLOUDFLARE_TUNNEL_TOKEN="):
                token = _clean_token(payload.split("=", 1)[1])
                if token and not _is_vault_reference(token):
                    return token

        if line.startswith("ExecStart="):
            command = line.split("=", 1)[1].strip()
            try:
                parts = shlex.split(command)
            except ValueError:
                parts = command.split()
            for index, part in enumerate(parts):
                if part == "--token" and index + 1 < len(parts):
                    token = _clean_token(parts[index + 1])
                    if token and not _is_vault_reference(token):
                        return token
                if part.startswith("--token="):
                    token = _clean_token(part.split("=", 1)[1])
                    if token and not _is_vault_reference(token):
                        return token

    return ""


def _vault_token(vault_secrets: dict[str, str] | None) -> str:
    if not vault_secrets:
        return ""
    for key in (
        "AXON_CLOUDFLARE_TUNNEL_TOKEN",
        "CLOUDFLARE_TUNNEL_TOKEN",
        "cloudflare_tunnel_token",
        "TUNNEL_TOKEN",
    ):
        token = _clean_token(vault_secrets.get(key))
        if token and not _is_vault_reference(token):
            return token
    return ""


def resolve_cloudflare_tunnel_token_state(
    stored_value: str | None = None,
    *,
    home_path: Path | None = None,
    vault_secrets: dict[str, str] | None = None,
) -> dict[str, str]:
    token = _clean_token(stored_value)
    if token and not _is_vault_reference(token):
        return {"token": token, "source": "settings"}

    has_vault_reference = _is_vault_reference(token)

    env_token = _clean_token(
        os.environ.get("AXON_CLOUDFLARE_TUNNEL_TOKEN")
        or os.environ.get("CLOUDFLARE_TUNNEL_TOKEN")
    )
    if env_token:
        return {"token": env_token, "source": "environment"}

    vault_token = _vault_token(vault_secrets)
    if vault_token:
        return {"token": vault_token, "source": "vault"}

    env_token = read_tunnel_token_from_env_file(legacy_tunnel_env_file(home_path=home_path))
    if env_token:
        return {"token": env_token, "source": "legacy_env_file"}

    service_token = read_tunnel_token_from_service_file(default_user_service_file(home_path=home_path))
    if service_token:
        return {"token": service_token, "source": "systemd_service"}

    if has_vault_reference and vault_secrets is not None:
        return {"token": "", "source": "vault_reference"}
    if has_vault_reference:
        return {"token": "", "source": "vault_reference"}
    return {"token": "", "source": "missing"}


def named_tunnel_ready(
    *,
    tunnel_mode: str,
    token_state: dict[str, str],
    stored_value: str | None = None,
) -> bool:
    mode = str(tunnel_mode or "trycloudflare").strip().lower()
    if mode != "named":
        return True
    if token_state.get("token"):
        return True
    return _is_vault_reference(stored_value) or token_state.get("source") == "vault_reference"
