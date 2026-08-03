"""DashPro Supabase Storage quota monitor (bounded port of axon-local slice)."""

from __future__ import annotations

import json
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request

from app.monitors.transport_retry import is_transient_transport_error, urlopen_with_retries


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


def _request_with_retries(
    request: Request,
    *,
    timeout: float,
    retries: int,
) -> tuple[int, str]:
    return urlopen_with_retries(
        request,
        timeout=max(1.0, float(timeout)),
        retries=max(0, int(retries)),
        backoff_seconds=0.5,
    )


def _supabase_rest_get_storage(
    headers: dict[str, str],
    path: str,
    *,
    timeout: float,
    retries: int,
) -> tuple[int, str]:
    base_url = headers["_base_url"]
    req = Request(
        f"{base_url}/rest/v1/{path}",
        method="GET",
        headers={
            k: v for k, v in headers.items() if not k.startswith("_")
        }
        | {"Accept-Profile": "storage"},
    )
    return _request_with_retries(req, timeout=timeout, retries=retries)


def _supabase_rpc_call(
    headers: dict[str, str],
    rpc_name: str,
    *,
    timeout: float,
    retries: int,
) -> tuple[int, str]:
    base_url = headers["_base_url"].rstrip("/")
    req = Request(
        f"{base_url}/rest/v1/rpc/{rpc_name}",
        method="POST",
        data=b"{}",
        headers={k: v for k, v in headers.items() if not k.startswith("_")},
    )
    return _request_with_retries(req, timeout=timeout, retries=retries)


def _format_storage_bytes(value: int) -> str:
    gigabytes = value / (1024 * 1024 * 1024)
    if gigabytes >= 1:
        return f"{gigabytes:.2f} GB"
    megabytes = value / (1024 * 1024)
    return f"{megabytes:.0f} MB"


def _transport_failure_detail(exc: Exception, *, attempts: int = 1) -> str:
    # Keep the shared " API query failed:" marker so inbox severity stays warning
    # (same ladder as PostHog/Sentry transport blips).
    detail = f"Supabase Storage API query failed: {exc}"
    if attempts > 1:
        detail = f"{detail} (after {attempts} attempts)"
    return detail


def _probe_storage_api_restricted(
    headers: dict[str, str],
    *,
    timeout: float,
    retries: int,
) -> tuple[str, str] | None:
    """Early Storage API probe for terminal outcomes.

    Returns:
      ("critical", detail) for HTTP 402 quota restriction
      None when unrestricted, non-402 HTTP, or transient network failures
      (usage fetch via RPC continues with its own retry budget)
    """
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
        status, body = _request_with_retries(req, timeout=timeout, retries=retries)
        if status == 402:
            return (
                "critical",
                f"Supabase Storage API restricted (402): {body[:200]}",
            )
    except HTTPError as exc:
        if int(exc.code) == 402:
            body = exc.read().decode("utf-8", errors="replace")
            return (
                "critical",
                f"Supabase Storage API restricted (402): {body[:200]}",
            )
        # Non-402 HTTP: let the usage fetch path decide / fall back.
        return None
    except (TimeoutError, URLError, OSError) as exc:
        if is_transient_transport_error(exc):
            return None
        return "warning", _transport_failure_detail(exc)
    return None


def _storage_api_request(
    headers: dict[str, str],
    path: str,
    *,
    method: str,
    timeout: float,
    retries: int,
    body: dict[str, object] | None = None,
) -> tuple[int, str]:
    base_url = headers["_base_url"].rstrip("/")
    payload = json.dumps(body).encode("utf-8") if body is not None else None
    request_headers = {
        "apikey": headers["apikey"],
        "Authorization": headers["Authorization"],
        "Accept": "application/json",
    }
    if body is not None:
        request_headers["Content-Type"] = "application/json"
    req = Request(
        f"{base_url}/storage/v1/{path.lstrip('/')}",
        method=method,
        data=payload,
        headers=request_headers,
    )
    return _request_with_retries(req, timeout=timeout, retries=retries)


def _object_size_bytes(row: dict[str, object]) -> int:
    candidates = []
    metadata = row.get("metadata")
    if isinstance(metadata, dict):
        candidates.append(metadata.get("size"))
    candidates.append(row.get("size"))
    for candidate in candidates:
        try:
            return int(candidate or 0)
        except (TypeError, ValueError):
            continue
    return 0


def _fetch_storage_bucket_totals_via_storage_api(
    headers: dict[str, str],
    *,
    timeout: float,
    retries: int,
    page_size: int = 100,
    max_requests: int = 200,
) -> tuple[dict[str, dict[str, int]], str | None]:
    deadline = time.monotonic() + min(timeout, 8.0)
    request_timeout = max(1.0, min(timeout, 5.0))
    attempts = max(1, int(retries) + 1)

    try:
        status, body = _storage_api_request(
            headers,
            "bucket",
            method="GET",
            timeout=request_timeout,
            retries=retries,
        )
    except HTTPError as exc:
        status = int(exc.code)
        body = exc.read().decode("utf-8", errors="replace")
        if status == 402:
            return {}, "402 exceed_storage_size_quota"
    except (TimeoutError, URLError, OSError) as exc:
        return {}, _transport_failure_detail(exc, attempts=attempts)

    if status == 402:
        return {}, "402 exceed_storage_size_quota"
    if status != 200:
        return {}, f"storage bucket list HTTP {status}: {body[:200]}"

    try:
        buckets = json.loads(body)
    except json.JSONDecodeError:
        return {}, "storage bucket list returned non-JSON payload"
    if not isinstance(buckets, list):
        return {}, "storage bucket list response was not a list"

    totals: dict[str, dict[str, int]] = {}
    request_count = 0
    for bucket in buckets:
        if not isinstance(bucket, dict):
            continue
        bucket_id = str(bucket.get("id") or bucket.get("name") or "").strip()
        if not bucket_id:
            continue
        totals[bucket_id] = {"bytes": 0, "count": 0}
        prefixes = [""]
        seen_prefixes = {""}
        while prefixes:
            if time.monotonic() >= deadline:
                return totals, "storage API time budget exceeded"
            prefix = prefixes.pop(0)
            offset = 0
            while True:
                if time.monotonic() >= deadline:
                    return totals, "storage API time budget exceeded"
                request_count += 1
                if request_count > max_requests:
                    return totals, "storage API pagination limit exceeded"
                try:
                    status, body = _storage_api_request(
                        headers,
                        f"object/list/{bucket_id}",
                        method="POST",
                        timeout=request_timeout,
                        retries=retries,
                        body={
                            "prefix": prefix,
                            "limit": page_size,
                            "offset": offset,
                            "sortBy": {"column": "name", "order": "asc"},
                        },
                    )
                except HTTPError as exc:
                    status = int(exc.code)
                    body = exc.read().decode("utf-8", errors="replace")
                    if status == 402:
                        return {}, "402 exceed_storage_size_quota"
                except (TimeoutError, URLError, OSError) as exc:
                    return totals, _transport_failure_detail(exc, attempts=attempts)

                if status == 402:
                    return {}, "402 exceed_storage_size_quota"
                if status != 200:
                    return totals, f"storage object list HTTP {status}: {body[:200]}"

                try:
                    rows = json.loads(body)
                except json.JSONDecodeError:
                    return totals, "storage object list returned non-JSON payload"
                if not isinstance(rows, list) or not rows:
                    break

                for row in rows:
                    if not isinstance(row, dict):
                        continue
                    name = str(row.get("name") or "").strip().strip("/")
                    if not name:
                        continue
                    metadata = row.get("metadata")
                    is_folder = (
                        not isinstance(metadata, dict)
                        and row.get("id") in {None, ""}
                    )
                    if is_folder:
                        child_prefix = f"{prefix}{name}/" if prefix else f"{name}/"
                        if child_prefix not in seen_prefixes:
                            seen_prefixes.add(child_prefix)
                            prefixes.append(child_prefix)
                        continue
                    totals[bucket_id]["bytes"] += _object_size_bytes(row)
                    totals[bucket_id]["count"] += 1

                if len(rows) < page_size:
                    break
                offset += page_size

    if totals:
        return totals, None
    return {}, "storage usage unavailable (no buckets or accessible objects)"


def _fetch_storage_bucket_totals(
    headers: dict[str, str],
    *,
    rpc_name: str,
    timeout: float,
    retries: int,
    page_size: int = 1000,
    max_pages: int = 50,
) -> tuple[dict[str, dict[str, int]], str | None]:
    attempts = max(1, int(retries) + 1)
    try:
        status, body = _supabase_rpc_call(
            headers,
            rpc_name,
            timeout=timeout,
            retries=retries,
        )
    except HTTPError as exc:
        status = int(exc.code)
        body = exc.read().decode("utf-8", errors="replace")
    except (TimeoutError, URLError, OSError) as exc:
        return {}, _transport_failure_detail(exc, attempts=attempts)

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
            status, body = _supabase_rest_get_storage(
                headers,
                path,
                timeout=timeout,
                retries=retries,
            )
        except HTTPError as exc:
            status = int(exc.code)
            body = exc.read().decode("utf-8", errors="replace")
            if status == 402:
                return {}, "402 exceed_storage_size_quota"
        except (TimeoutError, URLError, OSError) as exc:
            return totals, _transport_failure_detail(exc, attempts=attempts)

        if status == 402:
            return {}, "402 exceed_storage_size_quota"
        if status != 200:
            if status == 406:
                return _fetch_storage_bucket_totals_via_storage_api(
                    headers,
                    timeout=timeout,
                    retries=retries,
                )
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
        return _fetch_storage_bucket_totals_via_storage_api(
            headers,
            timeout=timeout,
            retries=retries,
        )
    return totals, None


def check_supabase_storage_quota(
    *,
    env: dict[str, str],
    quota_bytes: int = 1_073_741_824,
    warning_ratio: float = 0.80,
    critical_ratio: float = 0.90,
    rpc_name: str = "monitor_storage_bucket_usage",
    timeout_seconds: float = 20,
    retries: int = 2,
) -> tuple[str, str]:
    headers = _supabase_rest_headers(env)
    if not headers:
        return (
            "skipped",
            "Storage quota check skipped until Supabase URL and service-role key are available",
        )

    timeout = max(1.0, float(timeout_seconds))
    retry_count = max(0, int(retries))
    attempts = max(1, retry_count + 1)

    early = _probe_storage_api_restricted(
        headers,
        timeout=timeout,
        retries=retry_count,
    )
    if early is not None:
        return early

    totals, fetch_error = _fetch_storage_bucket_totals(
        headers,
        rpc_name=rpc_name,
        timeout=timeout,
        retries=retry_count,
    )
    if fetch_error == "402 exceed_storage_size_quota":
        return (
            "critical",
            "Supabase Storage is restricted (402 exceed_storage_size_quota). "
            "Purge regeneratable buckets (tts-audio first) or upgrade the plan.",
        )
    if fetch_error and not totals:
        # Transient network blips warn; auth/schema/quota failures stay critical.
        if " API query failed:" in fetch_error:
            return "warning", fetch_error
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
