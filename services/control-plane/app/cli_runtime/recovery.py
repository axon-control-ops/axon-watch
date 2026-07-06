"""Runtime candidate ordering and fallback policy for IDE composer execution."""

from __future__ import annotations

from typing import Any

StatusRecord = dict[str, Any]


def ordered_runtime_candidates(snapshot: dict[str, Any]) -> list[StatusRecord]:
    local = [record for record in list(snapshot.get("local") or []) if isinstance(record, dict)]
    cloud = [record for record in list(snapshot.get("cloud") or []) if isinstance(record, dict)]
    all_records = [*local, *cloud]
    by_id = {str(record.get("id") or ""): record for record in all_records}

    default_runtime = str(snapshot.get("default_runtime") or "").strip()
    default_record = by_id.get(default_runtime)
    preferred_family = str(default_record.get("family") or "") if default_record else ""

    ordered: list[StatusRecord] = []
    seen: set[str] = set()

    def add(record: StatusRecord) -> None:
        runtime_id = str(record.get("id") or "")
        if runtime_id and runtime_id not in seen:
            ordered.append(record)
            seen.add(runtime_id)

    if default_record:
        add(default_record)

    for record in local:
        if preferred_family and str(record.get("family") or "") == preferred_family:
            add(record)
    for record in cloud:
        if preferred_family and str(record.get("family") or "") == preferred_family:
            add(record)

    for record in local:
        if record.get("ready"):
            add(record)
    for record in cloud:
        if record.get("ready"):
            add(record)

    for record in local:
        add(record)
    for record in cloud:
        add(record)

    return ordered
