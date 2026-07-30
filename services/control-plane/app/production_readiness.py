"""Fleet production-readiness score for operator confidence."""

from __future__ import annotations

from typing import Any


def _cli_ready(cli_runtime: dict[str, Any] | None) -> tuple[bool, str | None]:
    if not isinstance(cli_runtime, dict) or not cli_runtime:
        return False, "CLI runtime readiness unknown"
    if bool(cli_runtime.get("dispatch_ready")) and bool(cli_runtime.get("default_ready")):
        return True, None
    blockers = cli_runtime.get("blockers")
    if isinstance(blockers, list) and blockers:
        return False, str(blockers[0] or "CLI runtime not ready").strip() or "CLI runtime not ready"
    return False, "CLI runtime not ready"


def build_production_readiness(
    *,
    watch_connected: bool,
    control_plane_ready: bool,
    degraded_active: bool,
    degraded_reasons: list[str] | None = None,
    cli_runtime: dict[str, Any] | None = None,
    critical_signal_count: int = 0,
    pending_approvals: int = 0,
    autonomy_mode: str = "manual",
    scheduler_effective: bool = False,
) -> dict[str, Any]:
    """Score 0–100 with explicit blockers. Ready means score >= 80 and no hard blockers."""
    checks: list[dict[str, Any]] = []
    blockers: list[str] = []
    score = 100

    def add_check(check_id: str, ok: bool, weight: int, detail: str) -> None:
        nonlocal score
        checks.append(
            {
                "id": check_id,
                "ok": ok,
                "weight": weight,
                "detail": detail,
            }
        )
        if not ok:
            score -= weight
            blockers.append(detail)

    add_check(
        "control_plane",
        control_plane_ready,
        20,
        "Control plane ready" if control_plane_ready else "Control plane not ready",
    )
    add_check(
        "watch",
        watch_connected,
        20,
        "Watch connected" if watch_connected else "Watch disconnected",
    )

    cli_ok, cli_detail = _cli_ready(cli_runtime)
    add_check(
        "cli_runtime",
        cli_ok,
        25,
        "CLI runtime ready" if cli_ok else (cli_detail or "CLI runtime not ready"),
    )

    degraded_ok = not degraded_active
    degraded_detail = "Runtime healthy"
    if degraded_active:
        reasons = [str(item).strip() for item in (degraded_reasons or []) if str(item).strip()]
        degraded_detail = reasons[0] if reasons else "Runtime degraded"
    add_check("runtime_health", degraded_ok, 15, degraded_detail)

    critical_ok = critical_signal_count <= 0
    add_check(
        "critical_signals",
        critical_ok,
        10,
        "No critical signals"
        if critical_ok
        else f"{critical_signal_count} critical signal(s) need attention",
    )

    approvals_ok = pending_approvals <= 0
    add_check(
        "approvals",
        approvals_ok,
        5,
        "No pending approvals"
        if approvals_ok
        else f"{pending_approvals} pending approval(s)",
    )

    mode = str(autonomy_mode or "manual").strip().lower()
    if mode == "full":
        add_check(
            "full_autonomy_workers",
            scheduler_effective,
            5,
            "Continuous workers running"
            if scheduler_effective
            else "Full autonomy selected but continuous workers are not effective",
        )
    else:
        checks.append(
            {
                "id": "full_autonomy_workers",
                "ok": True,
                "weight": 0,
                "detail": f"Autonomy mode is {mode} (workers optional)",
            }
        )

    score = max(0, min(100, score))
    hard_blockers = [
        item
        for item in blockers
        if not item.startswith("Autonomy mode") and "optional" not in item.lower()
    ]
    if score >= 80 and not hard_blockers:
        grade = "ready"
    elif score >= 50:
        grade = "partial"
    else:
        grade = "not_ready"

    return {
        "score": score,
        "grade": grade,
        "autonomy_mode": mode if mode in {"manual", "semi", "full"} else "manual",
        "blockers": blockers,
        "checks": checks,
        "summary": (
            f"Production is {score}%"
            + (f" — {blockers[0]}" if blockers else " — clear to operate with confidence")
        ),
    }


__all__ = ["build_production_readiness"]
