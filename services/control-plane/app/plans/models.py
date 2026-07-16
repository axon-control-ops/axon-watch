"""Plan artifact records."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class PlanRecord:
    plan_id: str
    workspace_id: str
    thread_id: str
    source_message_id: str
    title: str
    content: str
    path: str
    created_at: str
    updated_at: str

    def to_public_dict(self, *, include_content: bool = False) -> dict[str, Any]:
        payload = asdict(self)
        if not include_content:
            payload.pop("content", None)
        return payload
