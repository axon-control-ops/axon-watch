"""Safety policy for outbound research requests."""

from __future__ import annotations

import ipaddress
import json
import os
import socket
from pathlib import Path
from urllib.parse import urlparse


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def _policy_path() -> Path:
    override = str(os.environ.get("AXON_WATCH_RESEARCH_POLICY", "")).strip()
    if override:
        return Path(override).expanduser().resolve()
    return (_repo_root() / "config" / "research-policy.json").resolve()


def load_policy() -> dict[str, object]:
    path = _policy_path()
    if not path.is_file():
        return {"enabled": True, "deny_domains": [], "allow_domains": []}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def research_enabled() -> bool:
    if os.environ.get("AXON_WATCH_RESEARCH_ENABLED", "1").strip().lower() in {"0", "false", "no"}:
        return False
    return bool(load_policy().get("enabled", True))


def _hostname_allowed(hostname: str, policy: dict[str, object]) -> bool:
    host = hostname.strip().lower().rstrip(".")
    if not host:
        return False
    deny = {str(item).lower() for item in (policy.get("deny_domains") or [])}
    if host in deny:
        return False
    allow = [str(item).lower() for item in (policy.get("allow_domains") or []) if str(item).strip()]
    if allow and not any(host == item or host.endswith(f".{item}") for item in allow):
        return False
    return True


def _ip_is_public(address: str) -> bool:
    try:
        parsed = ipaddress.ip_address(address)
    except ValueError:
        return False
    return not (
        parsed.is_private
        or parsed.is_loopback
        or parsed.is_link_local
        or parsed.is_multicast
        or parsed.is_reserved
        or parsed.is_unspecified
    )


def validate_url(url: str) -> tuple[str, str]:
    """Return (normalized_url, hostname) or raise ValueError."""
    if not research_enabled():
        raise ValueError("online research is disabled")

    parsed = urlparse(url.strip())
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("only http(s) URLs are allowed")
    hostname = parsed.hostname or ""
    if not hostname:
        raise ValueError("URL hostname is required")

    policy = load_policy()
    if not _hostname_allowed(hostname, policy):
        raise ValueError(f"hostname blocked by research policy: {hostname}")

    for family in (socket.AF_INET, socket.AF_INET6):
        try:
            for info in socket.getaddrinfo(hostname, None, family, socket.SOCK_STREAM):
                ip = info[4][0]
                if not _ip_is_public(ip):
                    raise ValueError(f"refusing private or local address for {hostname}: {ip}")
        except socket.gaierror:
            continue

    normalized = parsed._replace(fragment="").geturl()
    return normalized, hostname
