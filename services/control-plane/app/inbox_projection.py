"""Project watch-produced inbox snapshots into UI-facing control-plane payloads."""

from __future__ import annotations

from typing import Callable

from app.adapters.watch_client import fetch_watch_inbox

WatchInboxFetcher = Callable[[], dict[str, object] | None]

_CONSISTENCY_FIELDS = ("signal_id", "severity", "status", "source")


class WatchInboxUnavailableError(RuntimeError):
    """Raised when the watch inbox fetch fails and must not look empty/healthy."""


def project_inbox_item(item: dict[str, object]) -> dict[str, object]:
    projected = {field: item[field] for field in _CONSISTENCY_FIELDS if field in item}
    projected.update(
        {
            "workspace_id": item.get("workspace_id", ""),
            "title": item.get("title", ""),
            "summary": item.get("summary", ""),
            "updated_at": item.get("updated_at", ""),
            "created_at": item.get("created_at", item.get("updated_at", "")),
            "action_type": item.get("action_type", "none"),
            "delivery_state": item.get("delivery_state", "pending"),
            "latest_receipt_id": item.get("latest_receipt_id", ""),
            "watch_rule": item.get(
                "watch_rule",
                {"mode": "observe", "reason": "ambient_watch_signal", "interrupts": False},
            ),
        }
    )
    if isinstance(item.get("meta"), dict):
        projected["meta"] = item["meta"]
    return projected


def project_watch_inbox(
    watch_inbox: dict[str, object] | None,
    *,
    allow_empty_unavailable: bool = False,
) -> dict[str, object]:
    if not watch_inbox:
        if allow_empty_unavailable:
            return {
                "items": [],
                "count": 0,
                "updated_at": "",
                "degraded": True,
                "error": "watch_unavailable",
            }
        raise WatchInboxUnavailableError("watch inbox unavailable")

    items = watch_inbox.get("items", [])
    if not isinstance(items, list):
        items = []

    projected_items = [project_inbox_item(item) for item in items if isinstance(item, dict)]
    return {
        "items": projected_items,
        "count": int(watch_inbox.get("count", len(projected_items))),
        "updated_at": str(watch_inbox.get("updated_at", "")),
        "degraded": False,
    }


def _merge_ci_remediation_items(
    projected: dict[str, object],
) -> dict[str, object]:
    """Overlay Gate 9 CI signals stored in control-plane onto watch inbox."""
    try:
        from app.ci_remediation.report import ci_inbox_items
    except Exception:  # noqa: BLE001 — inbox must stay available if module fails
        return projected
    ci_items = ci_inbox_items()
    if not ci_items:
        return projected
    existing = projected.get("items")
    items = [row for row in existing if isinstance(row, dict)] if isinstance(existing, list) else []
    seen = {
        str(row.get("signal_id") or "").strip()
        for row in items
        if str(row.get("signal_id") or "").strip()
    }
    merged = list(items)
    for raw in ci_items:
        projected_item = project_inbox_item(raw)
        signal_id = str(projected_item.get("signal_id") or "").strip()
        if signal_id and signal_id in seen:
            continue
        if signal_id:
            seen.add(signal_id)
        merged.insert(0, projected_item)
    out = dict(projected)
    out["items"] = merged
    out["count"] = len(merged)
    return out


def build_inbox_response(
    *,
    inbox_fetcher: WatchInboxFetcher | None = None,
    allow_empty_unavailable: bool = False,
) -> dict[str, object]:
    fetcher = inbox_fetcher or fetch_watch_inbox
    projected = project_watch_inbox(
        fetcher(),
        allow_empty_unavailable=allow_empty_unavailable,
    )
    return _merge_ci_remediation_items(projected)
