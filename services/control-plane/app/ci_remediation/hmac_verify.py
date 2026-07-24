"""HMAC verification for GitHub webhook deliveries."""

from __future__ import annotations

import hashlib
import hmac
import os


def github_webhook_secret() -> str:
    return (
        os.environ.get("AXON_WATCH_GITHUB_WEBHOOK_SECRET")
        or os.environ.get("GITHUB_WEBHOOK_SECRET")
        or ""
    ).strip()


def verify_github_signature(*, body: bytes, signature_header: str | None) -> bool:
    """Validate X-Hub-Signature-256. Empty secret rejects all (fail closed)."""
    secret = github_webhook_secret()
    if not secret:
        return False
    header = (signature_header or "").strip()
    if not header.startswith("sha256="):
        return False
    digest = header.removeprefix("sha256=")
    expected = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, digest)
