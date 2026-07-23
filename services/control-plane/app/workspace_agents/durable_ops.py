"""Gate 9 — restart-safe leases, idempotent effects, capacity/backoff controls."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


@dataclass
class EffectReceipt:
    effect_key: str
    effect_type: str
    payload_hash: str
    created_at: str = field(default_factory=lambda: _iso(_utc_now()))

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class IdempotentEffectLedger:
    """In-memory ledger (SQLite wiring can replace later) for duplicate-effect drills."""

    def __init__(self) -> None:
        self._effects: dict[str, EffectReceipt] = {}

    def claim(self, effect_key: str, effect_type: str, payload_hash: str) -> tuple[bool, EffectReceipt]:
        existing = self._effects.get(effect_key)
        if existing is not None:
            return False, existing
        receipt = EffectReceipt(
            effect_key=effect_key,
            effect_type=effect_type,
            payload_hash=payload_hash,
        )
        self._effects[effect_key] = receipt
        return True, receipt

    def get(self, effect_key: str) -> EffectReceipt | None:
        return self._effects.get(effect_key)


@dataclass
class TaskLease:
    task_id: str
    holder: str
    expires_at: str
    generation: int = 1

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class RestartSafeLeaseManager:
    def __init__(self) -> None:
        self._leases: dict[str, TaskLease] = {}

    def acquire(
        self,
        task_id: str,
        holder: str,
        *,
        ttl_seconds: int = 300,
        now: datetime | None = None,
    ) -> TaskLease:
        clock = now or _utc_now()
        current = self._leases.get(task_id)
        if current is not None:
            expires = datetime.fromisoformat(current.expires_at.replace("Z", "+00:00"))
            if expires > clock and current.holder != holder:
                raise RuntimeError(f"task {task_id} leased to {current.holder}")
            generation = current.generation + (0 if current.holder == holder else 1)
        else:
            generation = 1
        lease = TaskLease(
            task_id=task_id,
            holder=holder,
            expires_at=_iso(clock + timedelta(seconds=ttl_seconds)),
            generation=generation,
        )
        self._leases[task_id] = lease
        return lease

    def recover_expired(self, *, now: datetime | None = None) -> list[str]:
        clock = now or _utc_now()
        recovered: list[str] = []
        for task_id, lease in list(self._leases.items()):
            expires = datetime.fromisoformat(lease.expires_at.replace("Z", "+00:00"))
            if expires <= clock:
                del self._leases[task_id]
                recovered.append(task_id)
        return recovered


@dataclass
class ProjectCapacity:
    project_id: str
    max_inflight: int = 2
    inflight: int = 0
    dead_letters: list[str] = field(default_factory=list)
    backoff_until: str | None = None
    cost_used: int = 0
    cost_limit: int = 1_000_000
    stopped: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class FairSchedulerControls:
    def __init__(self) -> None:
        self._projects: dict[str, ProjectCapacity] = {}

    def ensure(self, project_id: str) -> ProjectCapacity:
        if project_id not in self._projects:
            self._projects[project_id] = ProjectCapacity(project_id=project_id)
        return self._projects[project_id]

    def can_dispatch(self, project_id: str, *, now: datetime | None = None) -> tuple[bool, str]:
        clock = now or _utc_now()
        cap = self.ensure(project_id)
        if cap.stopped:
            return False, "operator_stop"
        if cap.cost_used >= cap.cost_limit:
            return False, "cost_limit"
        if cap.backoff_until:
            until = datetime.fromisoformat(cap.backoff_until.replace("Z", "+00:00"))
            if until > clock:
                return False, "backoff"
        if cap.inflight >= cap.max_inflight:
            return False, "capacity"
        return True, "ok"

    def mark_dispatch(self, project_id: str, cost: int = 0) -> None:
        cap = self.ensure(project_id)
        cap.inflight += 1
        cap.cost_used += max(0, cost)

    def mark_complete(self, project_id: str) -> None:
        cap = self.ensure(project_id)
        cap.inflight = max(0, cap.inflight - 1)

    def dead_letter(self, project_id: str, task_id: str) -> None:
        cap = self.ensure(project_id)
        cap.dead_letters.append(task_id)
        self.mark_complete(project_id)

    def backoff(self, project_id: str, seconds: int = 60, *, now: datetime | None = None) -> None:
        clock = now or _utc_now()
        cap = self.ensure(project_id)
        cap.backoff_until = _iso(clock + timedelta(seconds=seconds))

    def operator_stop(self, project_id: str) -> None:
        self.ensure(project_id).stopped = True

    def operator_revoke_stop(self, project_id: str) -> None:
        self.ensure(project_id).stopped = False
