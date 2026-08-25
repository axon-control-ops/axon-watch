"""Control-plane email inbox route scoping tests."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi import HTTPException

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
if str(CONTROL_PLANE_ROOT) not in sys.path:
    sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.routes import inbox_watch  # noqa: E402


def test_email_folder_route_accepts_exact_account_id(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        inbox_watch.email_settings_store,
        "load_settings",
        lambda: {
            "accounts": [
                {
                    "account_id": "acct-ops",
                    "workspace_id": "workspace_axon_watch",
                    "email_address": "ops@example.com",
                }
            ]
        },
    )

    seen: dict[str, str] = {}

    def fake_fetch(account_id: str) -> dict[str, object]:
        seen["account_id"] = account_id
        return {"account_id": account_id, "folders": {"inbox": "INBOX"}}

    monkeypatch.setattr(inbox_watch, "fetch_watch_email_folders", fake_fetch)

    result = inbox_watch.email_folders(account_id="acct-ops")

    assert seen == {"account_id": "acct-ops"}
    assert result["account_id"] == "acct-ops"


def test_email_messages_route_rejects_unknown_account_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        inbox_watch.email_settings_store,
        "load_settings",
        lambda: {"accounts": [{"account_id": "acct-ops"}]},
    )

    with pytest.raises(HTTPException) as exc:
        inbox_watch.email_messages(account_id="acct-missing")

    assert exc.value.status_code == 404
    assert "acct-missing" in str(exc.value.detail)
