"""Inbox projection delivery adapter."""

from __future__ import annotations


def deliver_inbox(*, item: dict[str, object], signal_id: str) -> tuple[str, str, str]:
    _ = (item, signal_id)
    return ("succeeded", "", "inbox_projection_available")
