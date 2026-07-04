"""Project watch-produced inbox snapshots into UI-facing control-plane payloads."""

from __future__ import annotations

from typing import Callable

from app.adapters.watch_client import fetch_watch_inbox

WatchInboxFetcher = Callable[[], dict[str, object] | None]

_CONSISTENCY_FIELDS = ("signal_id", "severity", "status", "source")


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
        }
    )
    return projected


def project_watch_inbox(
    watch_inbox: dict[str, object] | None,
) -> dict[str, object]:
    if not watch_inbox:
        return {"items": [], "count": 0, "updated_at": ""}

    items = watch_inbox.get("items", [])
    if not isinstance(items, list):
        items = []

    projected_items = [project_inbox_item(item) for item in items if isinstance(item, dict)]
    return {
        "items": projected_items,
        "count": int(watch_inbox.get("count", len(projected_items))),
        "updated_at": str(watch_inbox.get("updated_at", "")),
    }


def build_inbox_response(
    *,
    inbox_fetcher: WatchInboxFetcher | None = None,
) -> dict[str, object]:
    fetcher = inbox_fetcher or fetch_watch_inbox
    return project_watch_inbox(fetcher())
