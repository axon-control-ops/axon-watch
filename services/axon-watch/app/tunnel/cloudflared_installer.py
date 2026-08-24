"""Install a pinned, checksum-verified cloudflared outside the repository.

Ordinary service startup must never reach the network for a binary, so this
module is only driven by explicit operator action (scripts/ops/install-cloudflared.sh
or the tunnel diagnostics rail). The supervisor consumes `installed_binary_path`
and reports `installer_diagnostics`, but never calls `install_cloudflared`.
"""

from __future__ import annotations

import hashlib
import json
import os
import platform
import shutil
import tempfile
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen

from app.tunnel.cloudflared_binary import cloudflared_version

_DOWNLOAD_HEADERS = {"User-Agent": "Axon-X-CloudflaredInstaller/1.0"}
_MAX_DOWNLOAD_BYTES = 256 * 1024 * 1024


class CloudflaredInstallError(RuntimeError):
    pass


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def default_pin_path() -> Path:
    configured = os.environ.get("AXON_WATCH_CLOUDFLARED_PIN_FILE", "").strip()
    if configured:
        path = Path(configured).expanduser()
        return path if path.is_absolute() else (_repo_root() / path).resolve()
    return (_repo_root() / "config" / "cloudflared-pin.json").resolve()


def load_pin(path: Path | None = None) -> dict[str, object]:
    pin_path = path or default_pin_path()
    try:
        payload = json.loads(pin_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CloudflaredInstallError(f"cloudflared pin file unreadable: {pin_path}") from exc
    if not isinstance(payload, dict) or not str(payload.get("version") or "").strip():
        raise CloudflaredInstallError(f"cloudflared pin file has no version: {pin_path}")
    return payload


def platform_key() -> str:
    return f"{platform.system().lower()}/{platform.machine().lower()}"


def pinned_artifact(pin: dict[str, object]) -> dict[str, str]:
    artifacts = pin.get("artifacts")
    key = platform_key()
    entry = artifacts.get(key) if isinstance(artifacts, dict) else None
    if not isinstance(entry, dict):
        raise CloudflaredInstallError(f"no pinned cloudflared artifact for platform {key}")
    asset = str(entry.get("asset") or "").strip()
    digest = str(entry.get("sha256") or "").strip().lower()
    # An unverifiable download is worse than no download: refuse rather than
    # install a binary that will terminate TLS for the whole control plane.
    if not asset or len(digest) != 64:
        raise CloudflaredInstallError(f"pinned artifact for {key} needs asset and sha256")
    return {"asset": asset, "sha256": digest}


def install_root(pin: dict[str, object] | None = None) -> Path:
    override = os.environ.get("AXON_WATCH_CLOUDFLARED_INSTALL_ROOT", "").strip()
    raw = override or str((pin or {}).get("install_root") or "").strip()
    expanded = os.path.expandvars(raw or "${HOME}/.local/lib/axon/cloudflared")
    return Path(expanded).expanduser()


def versioned_binary_path(pin: dict[str, object]) -> Path:
    return install_root(pin) / str(pin["version"]).strip() / "cloudflared"


def current_binary_path(pin: dict[str, object] | None = None) -> Path:
    return install_root(pin) / "current" / "cloudflared"


def installed_binary_path(pin: dict[str, object] | None = None) -> str:
    """Return the managed cloudflared path when it is present and executable."""

    candidate = current_binary_path(pin)
    return str(candidate) if os.access(candidate, os.X_OK) and candidate.is_file() else ""


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _download(url: str, destination: Path, *, timeout_seconds: float) -> int:
    written = 0
    try:
        request = Request(url, headers=dict(_DOWNLOAD_HEADERS))
        with urlopen(request, timeout=timeout_seconds) as response, destination.open("wb") as out:
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                written += len(chunk)
                if written > _MAX_DOWNLOAD_BYTES:
                    raise CloudflaredInstallError("cloudflared download exceeded size cap")
                out.write(chunk)
    except (URLError, TimeoutError, OSError, ValueError) as exc:
        raise CloudflaredInstallError(f"cloudflared download failed: {exc}") from exc
    if written == 0:
        raise CloudflaredInstallError("cloudflared download was empty")
    return written


def _point_current_at(root: Path, version: str) -> None:
    link = root / "current"
    pending = root / ".current.tmp"
    if pending.is_symlink() or pending.exists():
        pending.unlink()
    pending.symlink_to(version)
    # os.replace on a symlink swaps atomically, so readers never see it absent.
    os.replace(pending, link)


def install_cloudflared(
    *,
    pin: dict[str, object] | None = None,
    force: bool = False,
    timeout_seconds: float = 120.0,
) -> dict[str, object]:
    """Download, verify, and activate the pinned cloudflared. Operator-driven only."""

    pin = pin or load_pin()
    version = str(pin["version"]).strip()
    artifact = pinned_artifact(pin)
    target = versioned_binary_path(pin)
    root = install_root(pin)

    if target.is_file() and not force:
        actual = _sha256_file(target)
        if actual == artifact["sha256"]:
            _point_current_at(root, version)
            return {
                "ok": True,
                "changed": False,
                "version": version,
                "path": str(current_binary_path(pin)),
                "detail": "already installed",
            }

    base = str(pin.get("download_base_url") or "").strip().rstrip("/")
    if not base.startswith("https://"):
        raise CloudflaredInstallError("cloudflared download_base_url must be https")
    url = f"{base}/{version}/{artifact['asset']}"

    target.parent.mkdir(parents=True, exist_ok=True)
    handle, staged_name = tempfile.mkstemp(dir=str(target.parent), prefix=".cloudflared-")
    os.close(handle)
    staged = Path(staged_name)
    try:
        size = _download(url, staged, timeout_seconds=timeout_seconds)
        actual = _sha256_file(staged)
        if actual != artifact["sha256"]:
            raise CloudflaredInstallError(
                f"cloudflared checksum mismatch: expected {artifact['sha256']}, got {actual}"
            )
        staged.chmod(0o755)
        os.replace(staged, target)
    finally:
        if staged.exists():
            staged.unlink()

    _point_current_at(root, version)
    return {
        "ok": True,
        "changed": True,
        "version": version,
        "path": str(current_binary_path(pin)),
        "bytes": size,
        "detail": f"installed cloudflared {version}",
    }


def installer_diagnostics(pin: dict[str, object] | None = None) -> dict[str, object]:
    """Report managed-install state without touching the network."""

    try:
        pin = pin or load_pin()
    except CloudflaredInstallError as exc:
        return {"pinned_version": "", "installed": False, "reason": str(exc)}

    pinned_version = str(pin["version"]).strip()
    path = installed_binary_path(pin)
    version_output = cloudflared_version(path) if path else ""
    # `cloudflared --version` prints e.g. "cloudflared version 2026.8.2 (built ...)".
    installed_version = ""
    parts = version_output.split()
    if "version" in parts:
        index = parts.index("version")
        if index + 1 < len(parts):
            installed_version = parts[index + 1]

    supported = True
    reason = ""
    try:
        pinned_artifact(pin)
    except CloudflaredInstallError as exc:
        supported = False
        reason = str(exc)

    return {
        "pinned_version": pinned_version,
        "installed": bool(path),
        "installed_version": installed_version,
        "installed_path": path,
        "install_root": str(install_root(pin)),
        "platform": platform_key(),
        "platform_supported": supported,
        "upgrade_available": bool(path and installed_version and installed_version != pinned_version),
        "reason": reason or ("" if path else "managed cloudflared not installed"),
    }
