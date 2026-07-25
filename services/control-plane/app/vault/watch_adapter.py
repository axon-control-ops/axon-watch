"""Proxy vault operations to axon-watch internal APIs."""

from __future__ import annotations

import json
import mimetypes
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request

from app.adapters.watch_http import watch_request_headers, watch_urlopen

from app.adapters.watch_client import watch_base_url


def _raise_watch_error(exc: HTTPError) -> None:
    body = exc.read().decode("utf-8", errors="replace")
    detail = body
    try:
        parsed = json.loads(body)
        if isinstance(parsed, dict) and parsed.get("detail"):
            detail = str(parsed["detail"])
    except json.JSONDecodeError:
        pass
    raise RuntimeError(f"watch vault API HTTP {exc.code}: {detail[:300]}") from exc


def request_json(
    method: str,
    path: str,
    *,
    payload: dict[str, Any] | None = None,
    timeout_seconds: float = 15,
) -> Any:
    url = f"{watch_base_url()}{path}"
    data = None
    headers = watch_request_headers(
        content_type="application/json" if payload is not None else None
    )
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
    request = Request(url, data=data, method=method, headers=headers)
    try:
        with watch_urlopen(request, timeout=timeout_seconds) as response:
            body = response.read().decode("utf-8", errors="replace")
    except HTTPError as exc:
        _raise_watch_error(exc)
    except (TimeoutError, URLError, OSError) as exc:
        raise RuntimeError(f"watch vault API unavailable: {exc}") from exc

    if not body.strip():
        return {}
    try:
        return json.loads(body)
    except json.JSONDecodeError as exc:
        raise RuntimeError("watch vault API returned non-JSON payload") from exc


def request_bytes(
    method: str,
    path: str,
    *,
    payload: dict[str, Any] | None = None,
    timeout_seconds: float = 30,
) -> tuple[bytes, dict[str, str]]:
    url = f"{watch_base_url()}{path}"
    data = None
    headers = {"Accept": "*/*"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = Request(url, data=data, method=method, headers=headers)
    try:
        with watch_urlopen(request, timeout=timeout_seconds) as response:
            body = response.read()
            response_headers = {key.lower(): value for key, value in response.headers.items()}
            return body, response_headers
    except HTTPError as exc:
        _raise_watch_error(exc)
    except (TimeoutError, URLError, OSError) as exc:
        raise RuntimeError(f"watch vault API unavailable: {exc}") from exc


def request_multipart(
    path: str,
    *,
    fields: dict[str, str],
    file_field: str,
    filename: str,
    file_bytes: bytes,
    timeout_seconds: float = 30,
) -> dict[str, Any]:
    boundary = "----AxonWatchVaultBoundary7MA4YWxkTrZu0gW"
    content_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
    chunks: list[bytes] = []
    for name, value in fields.items():
        chunks.append(
            (
                f"--{boundary}\r\n"
                f'Content-Disposition: form-data; name="{name}"\r\n\r\n'
                f"{value}\r\n"
            ).encode("utf-8")
        )
    chunks.append(
        (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="{file_field}"; filename="{filename}"\r\n'
            f"Content-Type: {content_type}\r\n\r\n"
        ).encode("utf-8")
        + file_bytes
        + b"\r\n"
    )
    chunks.append(f"--{boundary}--\r\n".encode("utf-8"))
    body = b"".join(chunks)
    url = f"{watch_base_url()}{path}"
    request = Request(
        url,
        data=body,
        method="POST",
        headers={
            "Accept": "application/json",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        },
    )
    try:
        with watch_urlopen(request, timeout=timeout_seconds) as response:
            payload = response.read().decode("utf-8", errors="replace")
    except HTTPError as exc:
        _raise_watch_error(exc)
    except (TimeoutError, URLError, OSError) as exc:
        raise RuntimeError(f"watch vault API unavailable: {exc}") from exc
    parsed = json.loads(payload)
    if not isinstance(parsed, dict):
        raise RuntimeError("watch vault import response was not an object")
    return parsed


def fetch_watch_vault_snapshot() -> dict[str, Any]:
    payload = request_json("GET", "/internal/watch/vault/status")
    vault = payload.get("vault")
    if not isinstance(vault, dict):
        raise RuntimeError("watch vault status missing vault object")
    return vault


def post_watch_vault_monitor_import(
    secrets: dict[str, str],
    *,
    export_text: str = "",
) -> dict[str, Any]:
    payload: dict[str, Any] = {"secrets": secrets}
    if export_text.strip():
        payload["export_text"] = export_text
    response = request_json("POST", "/internal/watch/vault/import/monitor-keys", payload=payload)
    result = response.get("vault_import")
    if not isinstance(result, dict):
        raise RuntimeError("watch vault import missing vault_import object")
    return result


def post_watch_vault_backup_import(
    *,
    file_bytes: bytes,
    filename: str,
    backup_password: str = "",
    mode: str = "merge",
) -> dict[str, Any]:
    return request_multipart(
        "/internal/watch/vault/import",
        fields={"backup_password": backup_password, "mode": mode},
        file_field="file",
        filename=filename,
        file_bytes=file_bytes,
    )
