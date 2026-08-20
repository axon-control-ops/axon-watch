"""Fail-closed execution policy contracts for workspace employees."""

from __future__ import annotations

import shlex
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Any, Iterable, Mapping

from app.workspace_agents.execution_policy_prefixes import (
    COMMON_AUDITED_WRAPPERS as _COMMON_AUDITED_WRAPPERS, LEAD_DISPATCH_WRAPPERS as _LEAD_DISPATCH_WRAPPERS,
    COMMON_READ_PREFIXES as _COMMON_READ_PREFIXES,
    DOCUMENT_PREFIXES as _DOCUMENT_PREFIXES,
    GH_READ_PREFIXES as _GH_READ_PREFIXES,
    VALIDATION_PREFIXES as _VALIDATION_PREFIXES,
)


class ExecutionPolicyError(ValueError):
    """An execution policy is malformed or attempts an unknown policy mode."""


@dataclass(frozen=True, slots=True)
class AgentExecutionPolicy:
    """Immutable effective policy consumed by worker execution boundaries."""

    read_paths: tuple[str, ...]
    write_paths: tuple[str, ...]
    forbidden_path_globs: tuple[str, ...]
    approved_wrapper_names: tuple[str, ...]
    approved_command_prefixes: tuple[tuple[str, ...], ...]
    audited_capabilities: tuple[str, ...]
    network_mode: str
    timeout_seconds: int
    trust_policy: str
    execution_access: str

    @property
    def read_roots(self) -> tuple[str, ...]:
        """Compatibility name used by filesystem sandbox launchers."""

        return self.read_paths

    @property
    def writable_roots(self) -> tuple[str, ...]:
        """Compatibility name used by filesystem sandbox launchers."""

        return self.write_paths

    @property
    def approved_wrappers(self) -> tuple[str, ...]:
        """Compatibility name used by command-policy hooks."""

        return self.approved_wrapper_names


@dataclass(frozen=True, slots=True)
class AgentExecutionPolicyOverride:
    """Optional employee restrictions; omitted fields retain the role baseline."""

    read_paths: tuple[str, ...] | None = None
    write_paths: tuple[str, ...] | None = None
    forbidden_path_globs: tuple[str, ...] | None = None
    approved_wrapper_names: tuple[str, ...] | None = None
    approved_command_prefixes: tuple[tuple[str, ...], ...] | None = None
    audited_capabilities: tuple[str, ...] | None = None
    network_mode: str | None = None
    timeout_seconds: int | None = None
    trust_policy: str | None = None
    execution_access: str | None = None


_ROLE_DEFAULTS: dict[str, AgentExecutionPolicy] = {
    "lead": AgentExecutionPolicy(
        read_paths=(".",),
        write_paths=("node_modules", "docs/planning", "docs/ops", "docs", "output", "plans"),
        forbidden_path_globs=(),
        approved_wrapper_names=(*_COMMON_AUDITED_WRAPPERS, *_LEAD_DISPATCH_WRAPPERS, "run_contract_unit_tests.sh"),
        approved_command_prefixes=(
            *_COMMON_READ_PREFIXES,
            *_VALIDATION_PREFIXES,
            *_GH_READ_PREFIXES,
            *_DOCUMENT_PREFIXES,
        ),
        audited_capabilities=("planning_write", "test", "workspace_read", "ci_read", "dispatch"),
        network_mode="audited",
        timeout_seconds=900,
        trust_policy="worker",
        execution_access="full",
    ),
    "watcher": AgentExecutionPolicy(
        read_paths=(".",),
        write_paths=(),
        forbidden_path_globs=(),
        approved_wrapper_names=(*_COMMON_AUDITED_WRAPPERS, "axonhealth", "watch-fast-gate.sh"),
        approved_command_prefixes=_COMMON_READ_PREFIXES,
        audited_capabilities=("ci_read", "health", "workspace_read"),
        network_mode="audited",
        timeout_seconds=600,
        trust_policy="worker",
        execution_access="consultative",
    ),
    "frontend": AgentExecutionPolicy(
        read_paths=(".",),
        write_paths=(
            "node_modules",
            "apps",
            "app",
            "src",
            "website",
            "website/documents",
            "assets",
            "docs",
            "output",
            "scripts",
            "components",
            "features",
            "screens",
            "hooks",
            "packages",
            "tests",
            "__tests__",
            "locales",
        ),
        forbidden_path_globs=(),
        approved_wrapper_names=(*_COMMON_AUDITED_WRAPPERS, "console-web.sh"),
        approved_command_prefixes=(*_COMMON_READ_PREFIXES, *_VALIDATION_PREFIXES, *_DOCUMENT_PREFIXES),
        audited_capabilities=("build", "test", "workspace_read"),
        network_mode="none",
        timeout_seconds=1200,
        trust_policy="worker",
        execution_access="full",
    ),
    "backend": AgentExecutionPolicy(
        read_paths=(".",),
        write_paths=("node_modules", "services", "server", "api", "lib", "supabase", "packages", "tests"),
        forbidden_path_globs=(),
        approved_wrapper_names=(*_COMMON_AUDITED_WRAPPERS, "run_contract_unit_tests.sh"),
        approved_command_prefixes=(*_COMMON_READ_PREFIXES, *_VALIDATION_PREFIXES, *_DOCUMENT_PREFIXES),
        audited_capabilities=("build", "test", "workspace_read"),
        network_mode="none",
        timeout_seconds=1200,
        trust_policy="worker",
        execution_access="full",
    ),
    "integrations": AgentExecutionPolicy(
        read_paths=(".",),
        write_paths=("node_modules", ".github", "config", "scripts"),
        forbidden_path_globs=(),
        approved_wrapper_names=(*_COMMON_AUDITED_WRAPPERS, "axonhealth", "watch-fast-gate.sh"),
        approved_command_prefixes=(*_COMMON_READ_PREFIXES, *_VALIDATION_PREFIXES, *_GH_READ_PREFIXES),
        audited_capabilities=("ci_read", "health", "test", "workspace_read"),
        network_mode="audited",
        timeout_seconds=900,
        trust_policy="worker",
        execution_access="full",
    ),
}

_FALLBACK_POLICY = AgentExecutionPolicy(
    read_paths=(".",),
    write_paths=(),
    forbidden_path_globs=(),
    approved_wrapper_names=(),
    approved_command_prefixes=_COMMON_READ_PREFIXES,
    audited_capabilities=("workspace_read",),
    network_mode="none",
    timeout_seconds=600,
    trust_policy="worker",
    execution_access="consultative",
)

_NETWORK_RANK = {"none": 0, "audited": 1, "unrestricted": 2}
_TRUST_RANK = {"worker": 0, "operator": 1}
_ACCESS_RANK = {"consultative": 0, "full": 1}
_FRONTEND_UI_SCOPE_MARKERS = frozenset(
    {"apps", "app", "src", "components", "features", "screens", "locales"}
)
_ROLE_SAFE_TASK_SCOPE_EXPANSIONS: dict[str, tuple[tuple[str, frozenset[str]], ...]] = {
    # Frontend hooks are part of the UI implementation surface in React/Expo
    # apps.  Older task rows often leased app/components but omitted hooks,
    # which made normal hook edits look like a read-only checkout failure.  The
    # expansion stays bounded by the role baseline and workspace contract below.
    "frontend": (("hooks", _FRONTEND_UI_SCOPE_MARKERS),),
}
# Node/Express ops workspaces (Young Eagles command centre) store UI under
# command-centre/ and printable assets under output/, not apps/src/components.
_OPS_FRONTEND_WRITE_ROOTS = frozenset({"command-centre", "output"})


def _ops_frontend_write_paths_for_workspace(
    workspace_allowed_paths: Iterable[str] | None,
) -> tuple[str, ...]:
    """Grant Frontend write scope for ops-dashboard trees when the contract uses them."""
    if not workspace_allowed_paths:
        return ()
    workspace_scope = _normalize_paths(workspace_allowed_paths)
    workspace_roots = {
        path if path == "." else path.split("/", 1)[0] for path in workspace_scope
    }
    if "command-centre" not in workspace_roots:
        return ()
    candidates = _normalize_paths(tuple(sorted(_OPS_FRONTEND_WRITE_ROOTS)))
    return _intersect_path_scopes(candidates, workspace_scope)


def role_execution_policy(role: str) -> AgentExecutionPolicy:
    """Return an immutable conservative baseline for an employee role."""

    return _ROLE_DEFAULTS.get(_normalize_name(role), _FALLBACK_POLICY)


def default_write_scope_for_role(role: str) -> list[str]:
    """Write scope for a task that declared none — the role's own boundary.

    Returns the role's own write boundary as the fallback scope when a task
    declares no allowed_paths.  resolve_effective_policy treats task_allowed_paths=None
    as "no restriction", so passing these paths gives the task the role ceiling
    without granting anything beyond it.  A role that is read-only by design
    (watcher) still resolves to no write access.
    """

    return [str(path).strip() for path in role_execution_policy(role).write_paths if str(path).strip()]


def safe_task_write_scope_for_role(
    role: str,
    task_allowed_paths: Iterable[str],
) -> tuple[str, ...]:
    """Return a role-bounded task scope with safe conventional siblings restored.

    A task scope is still an authority boundary; this helper does not widen a
    run beyond the role baseline or workspace contract.  It only prevents stale
    leased scopes from excluding standard role-owned roots that are commonly
    required by the same implementation slice (for example React UI hooks).
    """

    normalized = _normalize_paths(task_allowed_paths)
    if not normalized:
        return normalized

    role_name = _normalize_name(role)
    additions = _ROLE_SAFE_TASK_SCOPE_EXPANSIONS.get(role_name, ())
    if not additions:
        return normalized

    role_roots = set(role_execution_policy(role_name).write_paths)
    present_roots = {
        path if path == "." else path.split("/", 1)[0]
        for path in normalized
    }
    expanded = list(normalized)
    for candidate, markers in additions:
        if candidate not in role_roots or candidate in present_roots:
            continue
        if present_roots & markers:
            expanded.append(candidate)
            present_roots.add(candidate)
    return _normalize_paths(expanded)


def parse_execution_policy_override(raw: Any) -> AgentExecutionPolicyOverride | None:
    """Parse an employee override while preserving omitted-versus-empty fields."""

    if raw is None:
        return None
    if not isinstance(raw, Mapping):
        raise ExecutionPolicyError("execution_policy must be a mapping")

    timeout_raw = raw.get("timeout_seconds", raw.get("timeout"))
    timeout: int | None = None
    if timeout_raw is not None:
        if isinstance(timeout_raw, bool):
            raise ExecutionPolicyError("timeout_seconds must be a positive integer")
        if isinstance(timeout_raw, float) and not timeout_raw.is_integer():
            raise ExecutionPolicyError("timeout_seconds must be a positive integer")
        try:
            timeout = int(timeout_raw)
        except (TypeError, ValueError) as exc:
            raise ExecutionPolicyError("timeout_seconds must be a positive integer") from exc
        if timeout <= 0:
            raise ExecutionPolicyError("timeout_seconds must be a positive integer")

    return AgentExecutionPolicyOverride(
        read_paths=_optional_paths(raw, "read_paths", "read_scope"),
        write_paths=_optional_paths(raw, "write_paths", "writable_paths", "write_scope"),
        forbidden_path_globs=_optional_strings(raw, "forbidden_path_globs"),
        approved_wrapper_names=_optional_strings(
            raw, "approved_wrapper_names", "approved_wrappers"
        ),
        approved_command_prefixes=_optional_command_prefixes(
            raw, "approved_command_prefixes", "command_prefixes"
        ),
        audited_capabilities=_optional_names(
            raw, "audited_capabilities", "capabilities"
        ),
        network_mode=_optional_mode(raw, "network_mode", _NETWORK_RANK),
        timeout_seconds=timeout,
        trust_policy=_optional_mode(raw, "trust_policy", _TRUST_RANK, "trust"),
        execution_access=_optional_mode(raw, "execution_access", _ACCESS_RANK),
    )


def resolve_effective_policy(
    *,
    role: str,
    employee_override: AgentExecutionPolicyOverride | None = None,
    workspace_allowed_paths: Iterable[str] | None,
    workspace_forbidden_path_globs: Iterable[str] | None = None,
    task_allowed_paths: Iterable[str] | None,
) -> AgentExecutionPolicy:
    """Intersect every authority source at a worker enforcement boundary.

    task_allowed_paths=None means "no task-level restriction" — the role's
    write_paths are used as-is after workspace intersection.  An explicit empty
    list still collapses write access to nothing (fail-closed).
    """

    baseline = role_execution_policy(role)
    override = employee_override

    read_paths = baseline.read_paths
    write_paths = baseline.write_paths
    wrappers = baseline.approved_wrapper_names
    command_prefixes = baseline.approved_command_prefixes
    capabilities = baseline.audited_capabilities
    forbidden = baseline.forbidden_path_globs
    network_mode = baseline.network_mode
    timeout_seconds = baseline.timeout_seconds
    trust_policy = baseline.trust_policy
    execution_access = baseline.execution_access

    if override is not None:
        if override.read_paths is not None:
            read_paths = _intersect_path_scopes(read_paths, override.read_paths)
        if override.write_paths is not None:
            write_paths = _intersect_path_scopes(write_paths, override.write_paths)
        if override.approved_wrapper_names is not None:
            wrappers = _intersect_exact(wrappers, override.approved_wrapper_names)
        if override.approved_command_prefixes is not None:
            command_prefixes = _intersect_command_prefixes(
                command_prefixes, override.approved_command_prefixes
            )
        if override.audited_capabilities is not None:
            capabilities = _intersect_exact(
                capabilities, override.audited_capabilities
            )
        if override.forbidden_path_globs is not None:
            forbidden = _ordered_union(forbidden, override.forbidden_path_globs)
        if override.network_mode is not None:
            network_mode = _stricter_mode(
                network_mode, override.network_mode, _NETWORK_RANK
            )
        if override.timeout_seconds is not None:
            timeout_seconds = min(timeout_seconds, override.timeout_seconds)
        if override.trust_policy is not None:
            trust_policy = _stricter_mode(
                trust_policy, override.trust_policy, _TRUST_RANK
            )
        if override.execution_access is not None:
            execution_access = _stricter_mode(
                execution_access, override.execution_access, _ACCESS_RANK
            )

    workspace_scope = _normalize_paths(workspace_allowed_paths or ())
    read_paths = _intersect_path_scopes(read_paths, workspace_scope)
    write_paths = _intersect_path_scopes(write_paths, workspace_scope)
    if task_allowed_paths is not None:
        task_scope = safe_task_write_scope_for_role(role, task_allowed_paths)
        write_paths = _intersect_path_scopes(write_paths, task_scope)
    forbidden = _ordered_union(
        forbidden, _normalize_strings(workspace_forbidden_path_globs or ())
    )

    if not write_paths and _normalize_name(role) == "frontend":
        write_paths = _ops_frontend_write_paths_for_workspace(workspace_allowed_paths)

    if not write_paths:
        execution_access = "consultative"

    return AgentExecutionPolicy(
        read_paths=read_paths,
        write_paths=write_paths,
        forbidden_path_globs=forbidden,
        approved_wrapper_names=wrappers,
        approved_command_prefixes=command_prefixes,
        audited_capabilities=capabilities,
        network_mode=network_mode,
        timeout_seconds=timeout_seconds,
        trust_policy=trust_policy,
        execution_access=execution_access,
    )


def _normalize_name(value: Any) -> str:
    return str(value or "").strip().lower().replace("-", "_").replace(" ", "_")


def _normalize_paths(values: Iterable[Any]) -> tuple[str, ...]:
    normalized: list[str] = []
    seen: set[str] = set()
    for value in values:
        raw = str(value or "").strip().replace("\\", "/")
        while raw.startswith("./"):
            raw = raw[2:]
        raw = raw.rstrip("/")
        if raw in {"", "."}:
            candidate = "."
        else:
            path = PurePosixPath(raw)
            if path.is_absolute() or ".." in path.parts:
                continue
            candidate = path.as_posix()
        key = candidate.casefold()
        if key not in seen:
            seen.add(key)
            normalized.append(candidate)
    return tuple(normalized)


def _normalize_strings(values: Iterable[Any]) -> tuple[str, ...]:
    return _ordered_union((), (str(value or "").strip() for value in values))


def _path_contains(parent: str, child: str) -> bool:
    if parent == ".":
        return True
    return child == parent or child.startswith(parent + "/")


def _intersect_path_scopes(
    left: Iterable[str], right: Iterable[str]
) -> tuple[str, ...]:
    left_scope = _normalize_paths(left)
    right_scope = _normalize_paths(right)
    if not left_scope or not right_scope:
        return ()
    result: list[str] = []
    for left_path in left_scope:
        for right_path in right_scope:
            if _path_contains(left_path, right_path):
                result.append(right_path)
            elif _path_contains(right_path, left_path):
                result.append(left_path)
    return _normalize_paths(result)


def _intersect_command_prefixes(
    left: Iterable[tuple[str, ...]], right: Iterable[tuple[str, ...]]
) -> tuple[tuple[str, ...], ...]:
    left_prefixes = _normalize_command_prefixes(left)
    right_prefixes = _normalize_command_prefixes(right)
    result: list[tuple[str, ...]] = []
    for left_prefix in left_prefixes:
        for right_prefix in right_prefixes:
            if right_prefix[: len(left_prefix)] == left_prefix:
                result.append(right_prefix)
            elif left_prefix[: len(right_prefix)] == right_prefix:
                result.append(left_prefix)
    return _normalize_command_prefixes(result)


def _intersect_exact(left: Iterable[str], right: Iterable[str]) -> tuple[str, ...]:
    allowed = {item.casefold() for item in _normalize_strings(right)}
    return tuple(item for item in _normalize_strings(left) if item.casefold() in allowed)


def _ordered_union(left: Iterable[str], right: Iterable[str]) -> tuple[str, ...]:
    result: list[str] = []
    seen: set[str] = set()
    for raw in (*tuple(left), *tuple(right)):
        value = str(raw or "").strip()
        key = value.casefold()
        if value and key not in seen:
            seen.add(key)
            result.append(value)
    return tuple(result)


def _stricter_mode(current: str, requested: str, ranks: Mapping[str, int]) -> str:
    if current not in ranks or requested not in ranks:
        raise ExecutionPolicyError("unknown execution policy mode")
    return min((current, requested), key=lambda value: ranks[value])


def _raw_optional(raw: Mapping[str, Any], *keys: str) -> tuple[bool, Any]:
    for key in keys:
        if key in raw:
            return True, raw[key]
    return False, None


def _coerce_sequence(value: Any, *, field_name: str) -> tuple[Any, ...]:
    if isinstance(value, str):
        return (value,)
    if isinstance(value, (list, tuple)):
        return tuple(value)
    raise ExecutionPolicyError(f"{field_name} must be a string or list")


def _optional_paths(raw: Mapping[str, Any], *keys: str) -> tuple[str, ...] | None:
    present, value = _raw_optional(raw, *keys)
    if not present:
        return None
    return _normalize_paths(_coerce_sequence(value, field_name=keys[0]))


def _optional_strings(raw: Mapping[str, Any], *keys: str) -> tuple[str, ...] | None:
    present, value = _raw_optional(raw, *keys)
    if not present:
        return None
    return _normalize_strings(_coerce_sequence(value, field_name=keys[0]))


def _optional_names(raw: Mapping[str, Any], *keys: str) -> tuple[str, ...] | None:
    values = _optional_strings(raw, *keys)
    if values is None:
        return None
    return tuple(_normalize_name(value) for value in values if _normalize_name(value))


def _normalize_command_prefixes(
    values: Iterable[Iterable[Any]],
) -> tuple[tuple[str, ...], ...]:
    result: list[tuple[str, ...]] = []
    seen: set[tuple[str, ...]] = set()
    for raw_prefix in values:
        prefix = tuple(str(token or "").strip() for token in raw_prefix)
        if not prefix or any(not token or "\x00" in token for token in prefix):
            continue
        if prefix not in seen:
            seen.add(prefix)
            result.append(prefix)
    return tuple(result)


def _optional_command_prefixes(
    raw: Mapping[str, Any], *keys: str
) -> tuple[tuple[str, ...], ...] | None:
    present, value = _raw_optional(raw, *keys)
    if not present:
        return None
    entries = _coerce_sequence(value, field_name=keys[0])
    parsed: list[tuple[str, ...]] = []
    for entry in entries:
        if isinstance(entry, str):
            try:
                tokens = tuple(shlex.split(entry, posix=True))
            except ValueError as exc:
                raise ExecutionPolicyError(
                    f"{keys[0]} contains malformed shell quoting"
                ) from exc
        elif isinstance(entry, (list, tuple)):
            tokens = tuple(str(token) for token in entry)
        else:
            raise ExecutionPolicyError(
                f"{keys[0]} entries must be command strings or token lists"
            )
        parsed.append(tokens)
    return _normalize_command_prefixes(parsed)


def _optional_mode(
    raw: Mapping[str, Any],
    key: str,
    modes: Mapping[str, int],
    *aliases: str,
) -> str | None:
    present, value = _raw_optional(raw, key, *aliases)
    if not present:
        return None
    normalized = _normalize_name(value)
    if normalized not in modes:
        raise ExecutionPolicyError(
            f"{key} must be one of: {', '.join(sorted(modes))}"
        )
    return normalized


__all__ = [
    "AgentExecutionPolicy",
    "AgentExecutionPolicyOverride",
    "ExecutionPolicyError",
    "parse_execution_policy_override",
    "resolve_effective_policy",
    "role_execution_policy",
    "safe_task_write_scope_for_role",
]
