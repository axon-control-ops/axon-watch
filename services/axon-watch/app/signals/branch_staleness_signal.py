"""Warn when a continuous worker's open PR spans many unrelated work sessions.

A continuous worker (e.g. Marco/backend) reuses one long-lived branch across
every task it is ever assigned, rather than a fresh branch per task. Old,
never-cleaned-up breakage from an unrelated task days earlier can sit
uncommitted-but-unfixed on that branch and silently ride along -- then break
CI for whatever new, perfectly-scoped task lands next, because the repo's
own CI (typecheck, lint, etc.) runs across the whole tree, not just the diff.
This surfaces that risk *before* it manifests as a confusing CI failure on
an unrelated task, by flagging an open worker/ branch whose commits already
span more than one calendar day.
"""

from __future__ import annotations

import json
import subprocess
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.signals.iso_time import utc_now_iso

_CACHE_TTL_SECONDS = 600.0
_cache: dict[str, tuple[float, list[dict[str, Any]]]] = {}
_refresh_lock = threading.Lock()
_refreshing = False

# Gate on the actual elapsed span between a branch's earliest and latest
# commit, not the count of distinct *calendar* days -- a branch with two
# commits four hours apart either side of UTC midnight already counts as
# "2 distinct calendar days" despite being the same work session. Elapsed
# span in real days is a much better proxy for "this branch has been
# reused across separate work sessions"; live-tested against 27 real open
# worker/ PRs, a >=3 day span cut cleanly between routine same-session
# branches (0-2 day span) and genuinely old, multi-session ones (19-22 day
# span) -- there was no ambiguous middle ground in that sample.
_STALE_SPAN_DAYS_THRESHOLD = 3
_WORKER_BRANCH_PREFIX = "worker/"
_GH_TIMEOUT_SECONDS = 15.0


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def _load_delivery_workspaces() -> list[dict[str, Any]]:
    path = _repo_root() / "config" / "workspace-delivery.json"
    if not path.is_file():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    workspaces = payload.get("workspaces")
    if not isinstance(workspaces, list):
        return []
    return [
        entry
        for entry in workspaces
        if isinstance(entry, dict) and entry.get("enabled", True)
    ]


def _gh(*args: str) -> str | None:
    try:
        result = subprocess.run(
            ["gh", *args],
            capture_output=True,
            text=True,
            timeout=_GH_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0:
        return None
    return result.stdout


def _open_worker_prs(owner: str, repo: str) -> list[dict[str, Any]]:
    out = _gh(
        "pr", "list",
        "--repo", f"{owner}/{repo}",
        "--state", "open",
        "--json", "number,headRefName,url,title",
        "--limit", "50",
    )
    if not out:
        return []
    try:
        prs = json.loads(out)
    except json.JSONDecodeError:
        return []
    if not isinstance(prs, list):
        return []
    return [
        pr
        for pr in prs
        if isinstance(pr, dict)
        and str(pr.get("headRefName") or "").startswith(_WORKER_BRANCH_PREFIX)
    ]


def _pr_commit_day_span(owner: str, repo: str, number: int) -> tuple[int, int] | None:
    """Return (distinct_calendar_days, span_days) across a PR's commits."""
    out = _gh(
        "api", f"repos/{owner}/{repo}/pulls/{number}/commits",
        "--jq", "[.[].commit.author.date]",
    )
    if not out:
        return None
    try:
        dates_raw = json.loads(out)
    except json.JSONDecodeError:
        return None
    if not isinstance(dates_raw, list) or not dates_raw:
        return None

    parsed: list[datetime] = []
    for raw in dates_raw:
        try:
            parsed.append(datetime.fromisoformat(str(raw).replace("Z", "+00:00")))
        except ValueError:
            continue
    if not parsed:
        return None

    distinct_days = {moment.astimezone(timezone.utc).date() for moment in parsed}
    span_days = (max(parsed) - min(parsed)).days
    return len(distinct_days), span_days


def _stale_branch_items(workspace_id: str, owner: str, repo: str) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    now = utc_now_iso()
    for pr in _open_worker_prs(owner, repo):
        number = pr.get("number")
        if not isinstance(number, int):
            continue
        stats = _pr_commit_day_span(owner, repo, number)
        if stats is None:
            continue
        distinct_days, span_days = stats
        if span_days < _STALE_SPAN_DAYS_THRESHOLD:
            continue

        branch = str(pr.get("headRefName") or "")
        url = str(pr.get("url") or "")
        title = str(pr.get("title") or "")
        items.append(
            {
                "signal_id": f"signal_branch_stale_{workspace_id}_{number}",
                "workspace_id": workspace_id,
                "title": f"Long-lived worker branch: PR #{number} spans {span_days} days",
                "summary": (
                    f'{branch} ("{title}") has commits spanning {span_days} days across '
                    f"{distinct_days} separate work sessions. Old, unrelated work from an "
                    "earlier task may still be riding along on this branch and can break "
                    "CI for whatever new, unrelated task lands next -- worth a fresh "
                    "branch per task or a targeted rebase before the next delivery."
                ),
                "severity": "warning",
                "status": "open",
                "source": "watch",
                "created_at": now,
                "updated_at": now,
                "action_type": "investigate",
                "delivery_state": "pending",
                "meta": {
                    "signal_family": "branch_staleness",
                    "pr_number": number,
                    "pr_url": url,
                    "branch": branch,
                    "distinct_commit_days": distinct_days,
                    "span_days": span_days,
                },
            }
        )
    return items


def _compute_items() -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for entry in _load_delivery_workspaces():
        workspace_id = str(entry.get("workspace_id") or "").strip()
        owner = str(entry.get("github_owner") or "").strip()
        repo = str(entry.get("github_repo") or "").strip()
        if not (workspace_id and owner and repo):
            continue
        items.extend(_stale_branch_items(workspace_id, owner, repo))
    return items


def _refresh_in_background() -> None:
    global _refreshing

    def _run() -> None:
        global _refreshing
        try:
            items = _compute_items()
            _cache["items"] = (time.monotonic(), items)
        finally:
            with _refresh_lock:
                _refreshing = False

    thread = threading.Thread(target=_run, name="branch-staleness-refresh", daemon=True)
    thread.start()


def branch_staleness_inbox_items() -> list[dict[str, Any]]:
    """Best-effort, never-blocking: this scans every configured repo's open
    PRs via `gh`, which can take tens of seconds cold. That is far too slow
    to sit inline in the inbox request path (it doubled as an accidental way
    to make the operator's "Refresh" button time out). Serve whatever is
    cached -- empty on a cold start -- and warm the cache in the background;
    the real result shows up on the next poll a few seconds later.
    """
    global _refreshing
    now = time.monotonic()
    cached = _cache.get("items")
    is_fresh = cached is not None and (now - cached[0]) < _CACHE_TTL_SECONDS

    if not is_fresh:
        with _refresh_lock:
            should_start = not _refreshing
            if should_start:
                _refreshing = True
        if should_start:
            _refresh_in_background()

    return list(cached[1]) if cached is not None else []
