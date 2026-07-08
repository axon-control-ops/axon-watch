"""DashPro Supabase Storage quota monitor (bounded port of axon-local slice)."""

from __future__ import annotations

import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def _supabase_rest_headers(env: dict[str, str]) -> dict[str, str] | None:
    url = str(
        env.get("EXPO_PUBLIC_SUPABASE_URL")
        or env.get("NEXT_PUBLIC_SUPABASE_URL")
        or ""
    ).strip().strip('"').strip("'")
    key = str(
        env.get("SUPABASE_SERVICE_ROLE_KEY")
        or env.get("SERVER_SUPABASE_SERVICE_ROLE_KEY")
        or ""
    ).strip().strip('"').strip("'")
    if not url or not key:
        return None
    return {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "_base_url": url,
    }


def _supabase_rest_get_storage(headers: dict[str, str], path: str, *, timeout: float) -> tuple[int, str]:
    base_url = headers["_base_url"]
    req = Request(
        f"{base_url}/rest/v1/{path}",
        method="GET",
        headers={
            k: v for k, v in headers.items() if not k.startswith("_")
        }
        | {"Accept-Profile": "storage"},
    )
    with urlopen(req, timeout=timeout) as response:
        return int(response.status), response.read().decode("utf-8", errors="replace")


def _supabase_rpc_call(headers: dict[str, str], rpc_name: str, *, timeout: float) -> tuple[int, str]:
    base_url = headers["_base_url"].rstrip("/")
    req = Request(
        f"{base_url}/rest/v1/rpc/{rpc_name}",
        method="POST",
        data=b"{}",
        headers={k: v for k, v in headers.items() if not k.startswith("_")},
    )
    with urlopen(req, timeout=timeout) as response:
        return int(response.status), response.read().decode("utf-8", errors="replace")


def _format_storage_bytes(value: int) -> str:
    gigabytes = value / (1024 * 1024 * 1024)
    if gigabytes >= 1:
        return f"{gigabytes:.2f} GB"
    megabytes = value / (1024 * 1024)
    return f"{megabytes:.0f} MB"


def _probe_storage_api_restricted(headers: dict[str, str], *, timeout: float) -> str | None:
    base_url = headers["_base_url"].rstrip("/")
    req = Request(
        f"{base_url}/storage/v1/bucket",
        method="GET",
        headers={
            "apikey": headers["apikey"],
            "Authorization": headers["Authorization"],
        },
    )
    try:
        with urlopen(req, timeout=timeout) as response:
            if int(response.status) == 402:
                body = response.read().decode("utf-8", errors="replace")
                return f"Supabase Storage API restricted (402): {body[:200]}"
    except HTTPError as exc:
        if int(exc.code) == 402:
            body = exc.read().decode("utf-8", errors="replace")
            return f"Supabase Storage API restricted (402): {body[:200]}"
        return f"Supabase Storage API probe failed: HTTP {exc.code}"
    except (TimeoutError, URLError, OSError) as exc:
        return f"Supabase Storage API probe failed: {exc}"
    return None


def _fetch_storage_bucket_totals(
    headers: dict[str, str],
    *,
    rpc_name: str,
    timeout: float,
    page_size: int = 1000,
    max_pages: int = 50,
) -> tuple[dict[str, dict[str, int]], str | None]:
    try:
        status, body = _supabase_rpc_call(headers, rpc_name, timeout=timeout)
    except HTTPError as exc:
        status = int(exc.code)
        body = exc.read().decode("utf-8", errors="replace")
    except (TimeoutError, URLError, OSError) as exc:
        return {}, f"storage usage RPC failed: {exc}"

    if status == 402:
        return {}, "402 exceed_storage_size_quota"
    if status == 200:
        try:
            rows = json.loads(body)
        except json.JSONDecodeError:
            return {}, "storage usage RPC returned non-JSON payload"
        if isinstance(rows, list):
            totals: dict[str, dict[str, int]] = {}
            for row in rows:
                if not isinstance(row, dict):
                    continue
                bucket_id = str(row.get("bucket_id") or "").strip()
                if not bucket_id:
                    continue
                totals[bucket_id] = {
                    "bytes": int(row.get("total_bytes") or 0),
                    "count": int(row.get("object_count") or 0),
                }
            if totals:
                return totals, None

    totals: dict[str, dict[str, int]] = {}
    offset = 0
    for _ in range(max_pages):
        path = f"objects?select=bucket_id,metadata&limit={page_size}&offset={offset}"
        try:
            status, body = _supabase_rest_get_storage(headers, path, timeout=timeout)
        except HTTPError as exc:
            status = int(exc.code)
            body = exc.read().decode("utf-8", errors="replace")
            if status == 402:
                return {}, "402 exceed_storage_size_quota"
        except (TimeoutError, URLError, OSError) as exc:
            return totals, f"storage.objects query failed: {exc}"

        if status == 402:
            return {}, "402 exceed_storage_size_quota"
        if status != 200:
            if totals:
                return totals, None
            return {}, f"storage.objects query HTTP {status}: {body[:200]}"

        try:
            rows = json.loads(body)
        except json.JSONDecodeError:
            return totals or {}, "storage.objects query returned non-JSON payload"
        if not isinstance(rows, list) or not rows:
            break

        for row in rows:
            if not isinstance(row, dict):
                continue
            bucket_id = str(row.get("bucket_id") or "").strip()
            if not bucket_id:
                continue
            metadata = row.get("metadata")
            size_raw = metadata.get("size") if isinstance(metadata, dict) else 0
            try:
                size_bytes = int(size_raw or 0)
            except (TypeError, ValueError):
                size_bytes = 0
            bucket = totals.setdefault(bucket_id, {"bytes": 0, "count": 0})
            bucket["bytes"] += size_bytes
            bucket["count"] += 1

        if len(rows) < page_size:
            break
        offset += page_size

    if not totals:
        return {}, "storage usage unavailable (apply monitor_storage_bucket_usage migration or check service-role access)"
    return totals, None


def check_supabase_storage_quota(
    *,
    env: dict[str, str],
    quota_bytes: int = 1_073_741_824,
    warning_ratio: float = 0.80,
    critical_ratio: float = 0.90,
    rpc_name: str = "monitor_storage_bucket_usage",
    timeout_seconds: float = 30,
) -> tuple[str, str]:
    headers = _supabase_rest_headers(env)
    if not headers:
        return (
            "skipped",
            "Storage quota check skipped until Supabase URL and service-role key are available",
        )

    restriction = _probe_storage_api_restricted(headers, timeout=timeout_seconds)
    if restriction:
        return "critical", restriction

    totals, fetch_error = _fetch_storage_bucket_totals(
        headers,
        rpc_name=rpc_name,
        timeout=timeout_seconds,
    )
    if fetch_error == "402 exceed_storage_size_quota":
        return (
            "critical",
            "Supabase Storage is restricted (402 exceed_storage_size_quota). "
            "Purge regeneratable buckets (tts-audio first) or upgrade the plan.",
        )
    if fetch_error and not totals:
        return "critical", fetch_error

    total_bytes = sum(bucket["bytes"] for bucket in totals.values())
    usage_ratio = total_bytes / max(1, quota_bytes)
    top_buckets = sorted(totals.items(), key=lambda item: item[1]["bytes"], reverse=True)[:5]
    bucket_summary = ", ".join(
        f"{bucket_id} {_format_storage_bytes(stats['bytes'])} ({stats['count']} files)"
        for bucket_id, stats in top_buckets
    )
    detail = (
        f"Supabase Storage {_format_storage_bytes(total_bytes)} / {_format_storage_bytes(quota_bytes)} "
        f"({usage_ratio * 100:.0f}%). Top buckets: {bucket_summary}"
    )

    if usage_ratio >= 1.0 or usage_ratio >= critical_ratio:
        return "critical", detail
    if usage_ratio >= warning_ratio:
        return "warning", detail
    return "ok", detail
