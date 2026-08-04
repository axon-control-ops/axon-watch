"""Best-effort local Claude Code usage telemetry.

Unlike Cursor, Anthropic does not expose a personal "current period usage"
endpoint the way Cursor's dashboard API does (`cursor_usage_probe.py` can
authenticate as the signed-in user and ask Cursor's servers directly).
Claude Code's OAuth session has no public equivalent, so this probe is
intentionally local-only and honest about that:

- Historical token / session / message counts come from the Claude Code
  CLI's own ``stats-cache.json`` (the same aggregate file the CLI itself
  maintains on disk) — real local telemetry, not a live account-quota API.
- "Usage limit reached" state is recorded live by callers that observe the
  actual Claude Code CLI failure text (see ``record_claude_usage_limit_hit``)
  so the console reflects a real, observed block instead of guessing one.
"""

from __future__ import annotations

import json
import os
import re
import threading
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

StatusRecord = dict[str, Any]

_USAGE_CACHE: dict[str, Any] = {"fetched_at": 0.0, "payload": None}
_USAGE_CACHE_TTL_SECONDS = 45.0
_USAGE_LOCK = threading.Lock()

_LIMIT_STATE: dict[str, Any] = {"hit_at": 0.0, "detail": "", "reset_epoch": None}
_LIMIT_LOCK = threading.Lock()
_LIMIT_WINDOW_SECONDS = 5 * 60 * 60  # Anthropic's Pro/Max rolling window is ~5h.
_RESET_EPOCH_RE = re.compile(r"\|\s*(\d{9,13})\b")

# Order-of-magnitude $/M-token planning rates, matching the disclaimer style
# already used for Cursor pricing in docs/how-to/auto-loop-and-credits.md —
# verify in the Anthropic Console. This produces an "API-equivalent" estimate
# only; Claude subscription plans (Pro/Max) are not metered per token.
_PRICE_PER_MTOK_USD: list[tuple[str, float, float]] = [
    ("opus", 15.0, 75.0),
    ("sonnet", 3.0, 15.0),
    ("haiku", 0.80, 4.0),
]
_CACHE_WRITE_MULTIPLIER = 1.25
_CACHE_READ_MULTIPLIER = 0.10
_DEFAULT_INPUT_RATE, _DEFAULT_OUTPUT_RATE = 3.0, 15.0


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _stats_cache_path() -> Path | None:
    override = str(os.environ.get("AXON_WATCH_CLAUDE_STATS_CACHE", "")).strip()
    if override:
        path = Path(override).expanduser()
        return path if path.is_file() else None
    candidates: list[Path] = []
    config_dir = str(os.environ.get("CLAUDE_CONFIG_DIR", "")).strip()
    if config_dir:
        candidates.append(Path(config_dir).expanduser() / "stats-cache.json")
    candidates.append(Path.home() / ".claude" / "stats-cache.json")
    for path in candidates:
        if path.is_file():
            return path
    return None


def _read_stats_cache() -> dict[str, Any] | None:
    path = _stats_cache_path()
    if path is None:
        return None
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError:
        return None
    try:
        parsed = json.loads(raw)
    except (json.JSONDecodeError, ValueError):
        return None
    return parsed if isinstance(parsed, dict) else None


def _rate_for_model(model_id: str) -> tuple[float, float]:
    lowered = model_id.lower()
    for needle, input_rate, output_rate in _PRICE_PER_MTOK_USD:
        if needle in lowered:
            return input_rate, output_rate
    return _DEFAULT_INPUT_RATE, _DEFAULT_OUTPUT_RATE


def _estimate_cost_usd(model_usage: dict[str, Any]) -> float | None:
    if not model_usage:
        return None
    total = 0.0
    for model_id, counters in model_usage.items():
        if not isinstance(counters, dict):
            continue
        input_rate, output_rate = _rate_for_model(str(model_id))
        input_tokens = float(counters.get("inputTokens") or 0)
        output_tokens = float(counters.get("outputTokens") or 0)
        cache_read = float(counters.get("cacheReadInputTokens") or 0)
        cache_write = float(counters.get("cacheCreationInputTokens") or 0)
        total += input_tokens / 1_000_000 * input_rate
        total += output_tokens / 1_000_000 * output_rate
        total += cache_read / 1_000_000 * input_rate * _CACHE_READ_MULTIPLIER
        total += cache_write / 1_000_000 * input_rate * _CACHE_WRITE_MULTIPLIER
    return round(total, 2)


def _recent_days(stats: dict[str, Any], *, days: int = 7) -> list[dict[str, Any]]:
    activity_by_date = {
        str(item.get("date")): item
        for item in stats.get("dailyActivity") or []
        if isinstance(item, dict) and item.get("date")
    }
    tokens_by_date = {
        str(item.get("date")): item.get("tokensByModel") or {}
        for item in stats.get("dailyModelTokens") or []
        if isinstance(item, dict) and item.get("date")
    }
    dates = sorted(set(activity_by_date) | set(tokens_by_date))[-days:]
    rows: list[dict[str, Any]] = []
    for date in dates:
        by_model = tokens_by_date.get(date) or {}
        activity = activity_by_date.get(date) or {}
        rows.append(
            {
                "date": date,
                "tokens": sum(int(v) for v in by_model.values() if isinstance(v, (int, float))),
                "messages": int(activity.get("messageCount") or 0),
                "sessions": int(activity.get("sessionCount") or 0),
                "tokens_by_model": by_model,
            }
        )
    return rows


def record_claude_usage_limit_hit(detail: str) -> None:
    """Remember a real Claude Code 'usage limit reached' failure seen by a caller.

    Callers own detecting the failure shape (``is_usage_limit_failure`` in
    ``failure_detail.py``); this only remembers the most recent hit so the
    console can reflect an observed block instead of inventing one from local
    telemetry alone. Claude Code's real limit message carries an optional
    ``|<epoch>`` reset suffix, which is parsed when present.
    """
    match = _RESET_EPOCH_RE.search(detail or "")
    reset_epoch: float | None = None
    if match:
        try:
            raw = int(match.group(1))
            reset_epoch = raw / 1000 if raw > 10_000_000_000 else float(raw)
        except (TypeError, ValueError):
            reset_epoch = None
    with _LIMIT_LOCK:
        _LIMIT_STATE["hit_at"] = time.time()
        _LIMIT_STATE["detail"] = str(detail or "").strip()
        _LIMIT_STATE["reset_epoch"] = reset_epoch


def reset_claude_usage_limit_state_for_tests() -> None:
    with _LIMIT_LOCK:
        _LIMIT_STATE["hit_at"] = 0.0
        _LIMIT_STATE["detail"] = ""
        _LIMIT_STATE["reset_epoch"] = None


def _active_limit_state() -> dict[str, Any] | None:
    with _LIMIT_LOCK:
        hit_at = float(_LIMIT_STATE.get("hit_at") or 0.0)
        if not hit_at:
            return None
        reset_epoch = _LIMIT_STATE.get("reset_epoch")
        now = time.time()
        if reset_epoch is not None and now >= float(reset_epoch):
            return None
        if reset_epoch is None and (now - hit_at) >= _LIMIT_WINDOW_SECONDS:
            return None
        return dict(_LIMIT_STATE)


def _reset_hint(limit_state: dict[str, Any] | None) -> str | None:
    if not limit_state:
        return None
    reset_epoch = limit_state.get("reset_epoch")
    if reset_epoch:
        reset_at = datetime.fromtimestamp(float(reset_epoch), tz=timezone.utc)
        return f"Resets around {reset_at.strftime('%H:%M UTC')}."
    hit_at = datetime.fromtimestamp(float(limit_state.get("hit_at") or 0.0), tz=timezone.utc)
    reset_guess = hit_at + timedelta(seconds=_LIMIT_WINDOW_SECONDS)
    return (
        f"Hit at {hit_at.strftime('%H:%M UTC')} — usually resets within ~5h "
        f"(around {reset_guess.strftime('%H:%M UTC')})."
    )


def claude_usage_allows_agent_retry(usage: StatusRecord | None) -> bool:
    """True unless a real 'usage limit reached' signal is still within its window."""
    if not isinstance(usage, dict):
        return True
    return not bool(usage.get("limit_reached"))


def probe_claude_usage(*, force_refresh: bool = False) -> StatusRecord:
    """Return local Claude Code usage telemetry for Runtime status / console indicator."""
    cached = _USAGE_CACHE.get("payload")
    fetched_at = float(_USAGE_CACHE.get("fetched_at") or 0.0)
    if (
        not force_refresh
        and cached is not None
        and (time.monotonic() - fetched_at) < _USAGE_CACHE_TTL_SECONDS
    ):
        return dict(cached)

    with _USAGE_LOCK:
        cached = _USAGE_CACHE.get("payload")
        fetched_at = float(_USAGE_CACHE.get("fetched_at") or 0.0)
        if (
            not force_refresh
            and cached is not None
            and (time.monotonic() - fetched_at) < _USAGE_CACHE_TTL_SECONDS
        ):
            return dict(cached)

        stats = _read_stats_cache()
        limit_state = _active_limit_state()
        reset_hint = _reset_hint(limit_state)

        if stats is None:
            payload: StatusRecord = {
                "ok": False,
                "source": "unavailable",
                "updated_at": _utc_now_iso(),
                "recent_days": [],
                "most_recent_day": None,
                "tokens_7d": None,
                "total_sessions": None,
                "total_messages": None,
                "lifetime_estimated_cost_usd": None,
                "limit_reached": limit_state is not None,
                "limit_reset_hint": reset_hint,
                "message": "Claude Code local usage telemetry unavailable on this host.",
                "display_message": None,
                "allows_agent_retry": limit_state is None,
            }
        else:
            recent = _recent_days(stats)
            most_recent = recent[-1] if recent else None
            tokens_7d = sum(int(row["tokens"]) for row in recent) if recent else None
            model_usage = stats.get("modelUsage")
            model_usage = model_usage if isinstance(model_usage, dict) else {}
            lifetime_cost = _estimate_cost_usd(model_usage)
            display_message = (
                f"Most recent logged day {most_recent['date']}: "
                f"{most_recent['tokens']:,} tokens · {most_recent['messages']} messages"
                if most_recent
                else None
            )
            payload = {
                "ok": True,
                "source": "claude_code_local_stats",
                "updated_at": _utc_now_iso(),
                "recent_days": recent,
                "most_recent_day": most_recent,
                "tokens_7d": tokens_7d,
                "total_sessions": stats.get("totalSessions"),
                "total_messages": stats.get("totalMessages"),
                "lifetime_estimated_cost_usd": lifetime_cost,
                "limit_reached": limit_state is not None,
                "limit_reset_hint": reset_hint,
                "message": "Local Claude Code usage telemetry (not a live account-quota API).",
                "display_message": display_message,
                "allows_agent_retry": limit_state is None,
            }
        _USAGE_CACHE["fetched_at"] = time.monotonic()
        _USAGE_CACHE["payload"] = dict(payload)
        return dict(payload)


__all__ = [
    "claude_usage_allows_agent_retry",
    "probe_claude_usage",
    "record_claude_usage_limit_hit",
    "reset_claude_usage_limit_state_for_tests",
]
