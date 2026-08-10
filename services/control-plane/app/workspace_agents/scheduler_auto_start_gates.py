"""Auto-start skip gates for continuous worker ticks (usage + billing + runtime auth)."""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.workspace_agents.failure_detail import (
    is_billing_block_failure,
    is_billing_failure,
    is_runtime_auth_failure,
    is_shift_continuation_failure,
    is_usage_limit_failure,
)
from app.workspace_agents.run_outcome import latest_role_run_outcome

logger = logging.getLogger(__name__)


def usage_limit_blocks_auto_start(workspace_id: str, role: str) -> bool:
    """Skip auto-schedule for this role when its last shift failed on usage limits.

    Soft-open when the runtime that *actually failed* still shows headroom.
    ``is_usage_limit_failure`` matches generic phrasing ("usage limit", "out of
    usage", ...) that both Cursor and Claude Code can produce, but this used
    to always consult Cursor's pool regardless of which CLI failed — so a
    Claude usage-limit failure could never soft-open (Claude never has Cursor
    headroom) and, worse, could falsely soft-open off leftover Cursor
    headroom that has nothing to do with the Claude block. Route to the probe
    for the runtime named in the failure detail instead.
    """
    outcome = latest_role_run_outcome(workspace_id, role)
    if not outcome or str(outcome.get("outcome") or "").strip().lower() != "failed":
        return False
    detail = str(outcome.get("detail") or "")
    if not is_usage_limit_failure(detail):
        return False

    lowered = detail.lower()
    try:
        if "claude" in lowered:
            from app.cli_runtime.claude_usage_probe import (
                claude_usage_allows_agent_retry,
                probe_claude_usage,
                record_claude_usage_limit_hit,
            )

            record_claude_usage_limit_hit(detail)
            if claude_usage_allows_agent_retry(probe_claude_usage()):
                return False
        elif "codex" in lowered:
            from app.cli_runtime.codex_usage_probe import (
                codex_usage_allows_agent_retry,
                probe_codex_usage,
                record_codex_usage_limit_hit,
            )

            record_codex_usage_limit_hit(detail)
            if codex_usage_allows_agent_retry(probe_codex_usage()):
                return False
        else:
            # Cursor remains the default/legacy source of this failure shape;
            # unknown runtimes fall back to the Cursor pool check too.
            from app.cli_runtime.cursor_usage_probe import (
                cursor_usage_allows_agent_retry,
                probe_cursor_usage,
            )

            if cursor_usage_allows_agent_retry(probe_cursor_usage()):
                return False
    except Exception:
        pass
    return True


def billing_block_blocks_auto_start(workspace_id: str, role: str) -> bool:
    """Skip auto-schedule when the last shift failed on an unpaid Cursor invoice.

    No soft-open via usage headroom — Stripe invoice holds fail agent starts even
    when Auto/Composer still look available. Clears once a later role outcome is
    no longer an unpaid-invoice failure (manual retry after payment).
    """
    outcome = latest_role_run_outcome(workspace_id, role)
    if not outcome or str(outcome.get("outcome") or "").strip().lower() != "failed":
        return False
    detail = str(outcome.get("detail") or "")
    return is_billing_block_failure(detail)


def workspace_usage_limit_blocks_auto_start(workspace_id: str, roles: list[str]) -> bool:
    """Deprecated account-wide gate — kept for import compatibility; always False.

    Cursor pools are not a single hard stop for every role when Auto/on-demand remain.
    """
    del workspace_id, roles
    return False


def runtime_auth_blocks_auto_start(workspace_id: str, role: str) -> bool:
    """Skip auto-schedule when the last shift failed on missing CLI/vault auth.

    Soft-open after a successful Cursor auth heal — probe timeouts should not
    permanently quarantine a role once the host CLI is signed in again.
    """
    outcome = latest_role_run_outcome(workspace_id, role)
    if not outcome or str(outcome.get("outcome") or "").strip().lower() != "failed":
        return False
    detail = str(outcome.get("detail") or "")
    if not is_runtime_auth_failure(detail):
        return False
    try:
        from app.cli_runtime.catalog_snapshot import (
            recover_cursor_auth_synchronously,
            snapshot_has_auth_probe_timeout,
        )
        from app.cli_runtime.readiness import summarize_cli_runtime_readiness

        if "auth probe timed out" in detail.lower() or "timed out" in detail.lower():
            snapshot = recover_cursor_auth_synchronously()
            summary = summarize_cli_runtime_readiness(snapshot)
            if bool(summary.get("dispatch_ready")) and not snapshot_has_auth_probe_timeout(
                snapshot
            ):
                return False
    except Exception:
        pass
    return True


_BILLING_COOLDOWN_SECONDS = 1800.0  # 30 minutes


def _billing_cooldown_state_path() -> Path:
    raw = os.environ.get("AXON_WATCH_STATE_DIR", "./.local/state").strip() or "./.local/state"
    root = Path(raw).expanduser()
    if not root.is_absolute():
        root = (Path.cwd() / root).resolve()
    return root / "billing-retry-cooldown.json"


def _load_billing_cooldown_state(path: Path | None = None) -> dict[str, Any]:
    target = path or _billing_cooldown_state_path()
    if not target.is_file():
        return {}
    try:
        payload = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _save_billing_cooldown_state(state: dict[str, Any], path: Path | None = None) -> None:
    target = path or _billing_cooldown_state_path()
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except OSError:
        logger.exception("could not persist billing retry cooldown state")


def _parse_iso(raw: str | None) -> datetime | None:
    text = str(raw or "").strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None


def billing_blocks_auto_start(
    workspace_id: str,
    role: str,
    *,
    now: datetime | None = None,
    state_path: Path | None = None,
) -> bool:
    """Skip auto-schedule when the last shift failed on billing/credits.

    Unlike usage limits or auth, there's no cheap probe for "has the account
    been topped up" — the CLI itself is authenticated, the account is just
    out of funds. Retrying every 45s scheduler tick just re-hits the same
    wall indefinitely (the original bug: an unpaid-invoice or out-of-credits
    role got redispatched, full system prompt and all, forever). Block for a
    fixed cooldown instead of indefinitely, so it recovers on its own if the
    operator fixes billing without needing to find and clear a manual flag.
    """
    outcome = latest_role_run_outcome(workspace_id, role)
    if not outcome or str(outcome.get("outcome") or "").strip().lower() != "failed":
        return False
    detail = str(outcome.get("detail") or "")
    if not is_billing_failure(detail):
        return False

    run_id = str(outcome.get("run_id") or "").strip()
    key = f"{workspace_id}:{role}"
    current = now or datetime.now(timezone.utc)
    state = _load_billing_cooldown_state(state_path)
    entry = state.get(key)

    if not isinstance(entry, dict) or entry.get("run_id") != run_id:
        # First time we've seen this particular failed run — start the cooldown.
        state[key] = {
            "run_id": run_id,
            "first_blocked_at": current.isoformat().replace("+00:00", "Z"),
        }
        _save_billing_cooldown_state(state, state_path)
        return True

    first_blocked = _parse_iso(str(entry.get("first_blocked_at") or ""))
    if first_blocked is None:
        return True
    if first_blocked.tzinfo is None:
        first_blocked = first_blocked.replace(tzinfo=timezone.utc)
    elapsed = (current - first_blocked.astimezone(timezone.utc)).total_seconds()
    return elapsed < _BILLING_COOLDOWN_SECONDS


# Escalating backoff for any repeated failure the gates above don't already
# recognize (usage limits / billing / runtime auth). Without this, an
# unclassified failure — a CLI self-update race, a transient recursion bug,
# any error nobody wrote a specific gate for — gets retried on every 45s
# scheduler tick indefinitely: the same task fails, gets re-leased 45s later,
# fails again, forever, burning a full dispatch (and system prompt) each
# time. 2m -> 5m -> 15m -> 30m, capped, resetting once a shift succeeds.
_GENERIC_BACKOFF_SCHEDULE_SECONDS = (120.0, 300.0, 900.0, 1800.0)


def _generic_retry_cooldown_state_path() -> Path:
    raw = os.environ.get("AXON_WATCH_STATE_DIR", "./.local/state").strip() or "./.local/state"
    root = Path(raw).expanduser()
    if not root.is_absolute():
        root = (Path.cwd() / root).resolve()
    return root / "generic-retry-cooldown.json"


def _load_generic_retry_cooldown_state(path: Path | None = None) -> dict[str, Any]:
    target = path or _generic_retry_cooldown_state_path()
    if not target.is_file():
        return {}
    try:
        payload = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _save_generic_retry_cooldown_state(state: dict[str, Any], path: Path | None = None) -> None:
    target = path or _generic_retry_cooldown_state_path()
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except OSError:
        logger.exception("could not persist generic retry cooldown state")


def generic_repeated_failure_blocks_auto_start(
    workspace_id: str,
    role: str,
    *,
    now: datetime | None = None,
    state_path: Path | None = None,
) -> bool:
    """Escalating cooldown for failures none of the specific gates recognize.

    Deliberately excludes anything the other gates already classify (they
    have smarter, sometimes soft-opening logic); this is only the catch-all
    for everything else, so an unanticipated error class still gets a
    backoff instead of being retried every tick forever.
    """
    key = f"{workspace_id}:{role}"
    outcome = latest_role_run_outcome(workspace_id, role)
    if not outcome or str(outcome.get("outcome") or "").strip().lower() != "failed":
        # A successful (or no-history) shift clears any prior streak, so a
        # role that recovers and later fails again starts a fresh backoff
        # instead of inheriting an escalated cooldown from an old streak.
        state = _load_generic_retry_cooldown_state(state_path)
        if key in state:
            del state[key]
            _save_generic_retry_cooldown_state(state, state_path)
        return False
    detail = str(outcome.get("detail") or "")
    if (
        is_usage_limit_failure(detail)
        or is_billing_block_failure(detail)
        or is_billing_failure(detail)
        or is_runtime_auth_failure(detail)
        or is_shift_continuation_failure(detail)
    ):
        return False

    run_id = str(outcome.get("run_id") or "").strip()
    current = now or datetime.now(timezone.utc)
    state = _load_generic_retry_cooldown_state(state_path)
    entry = state.get(key)

    if not isinstance(entry, dict) or entry.get("run_id") != run_id:
        prior_streak = int(entry.get("streak") or 0) if isinstance(entry, dict) else 0
        state[key] = {
            "run_id": run_id,
            "first_blocked_at": current.isoformat().replace("+00:00", "Z"),
            "streak": prior_streak + 1,
        }
        _save_generic_retry_cooldown_state(state, state_path)
        return True

    streak = max(int(entry.get("streak") or 1), 1)
    cooldown = _GENERIC_BACKOFF_SCHEDULE_SECONDS[
        min(streak - 1, len(_GENERIC_BACKOFF_SCHEDULE_SECONDS) - 1)
    ]
    first_blocked = _parse_iso(str(entry.get("first_blocked_at") or ""))
    if first_blocked is None:
        return True
    if first_blocked.tzinfo is None:
        first_blocked = first_blocked.replace(tzinfo=timezone.utc)
    elapsed = (current - first_blocked.astimezone(timezone.utc)).total_seconds()
    return elapsed < cooldown


def continuous_auto_start_skip_reason(workspace_id: str, role: str) -> str | None:
    """Return a skip reason for continuous ticks, or None when the role may start."""
    if usage_limit_blocks_auto_start(workspace_id, role):
        return "Cursor usage limits blocked this role's last shift"
    if billing_block_blocks_auto_start(workspace_id, role):
        return "Cursor unpaid invoice blocked this role's last shift"
    if billing_blocks_auto_start(workspace_id, role):
        return "billing/credits failure blocked this role's last shift"
    if runtime_auth_blocks_auto_start(workspace_id, role):
        return "runtime auth blocked last shift"
    if generic_repeated_failure_blocks_auto_start(workspace_id, role):
        return "repeated unclassified failure blocked this role's last shift (backing off)"
    return None
