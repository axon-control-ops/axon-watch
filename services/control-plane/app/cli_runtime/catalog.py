"""Discover local CLI runtimes and expose a boot-safe status snapshot."""

from __future__ import annotations

import copy
import os
import shutil
import subprocess
import time
from datetime import datetime, timezone
from typing import Any

from app.cli_runtime.vault_keys import fetch_runtime_context
from app.cli_runtime.runtime_auth import env_without_api_keys

StatusRecord = dict[str, Any]

_SNAPSHOT_CACHE: dict[str, Any] = {"fetched_at": 0.0, "payload": None}
_CACHE_TTL_SECONDS = 30.0


def invalidate_runtime_snapshot_cache() -> None:
    _SNAPSHOT_CACHE["fetched_at"] = 0.0
    _SNAPSHOT_CACHE["payload"] = None


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _truthy_env(value: object) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def cli_runtime_family(path: str = "") -> str:
    candidate = os.path.basename(str(path or "")).strip().lower()
    if candidate == "cursor":
        return "cursor"
    if "codex" in candidate:
        return "codex"
    return ""


def _is_executable(path: str) -> bool:
    return bool(path) and os.path.isfile(path) and os.access(path, os.X_OK)


def _run_command(parts: list[str], *, timeout: int = 15, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        parts,
        capture_output=True,
        text=True,
        timeout=timeout,
        env=env or {**os.environ, "NO_COLOR": "1"},
    )


def find_cursor_cli(override_path: str = "") -> str:
    if _is_executable(override_path) and cli_runtime_family(override_path) == "cursor":
        return override_path
    for candidate in (
        shutil.which("cursor") or "",
        os.path.expanduser("~/.local/bin/cursor"),
        os.path.expanduser("~/bin/cursor"),
    ):
        if _is_executable(candidate):
            return candidate
    return ""


def find_codex_cli(override_path: str = "") -> str:
    if _is_executable(override_path) and cli_runtime_family(override_path) == "codex":
        return override_path
    for candidate in (
        shutil.which("codex") or "",
        os.path.expanduser("~/.local/bin/codex"),
        os.path.expanduser("~/bin/codex"),
        os.path.expanduser("~/.npm-global/bin/codex"),
        os.path.expanduser("~/.volta/bin/codex"),
    ):
        if _is_executable(candidate):
            return candidate
    return ""


def _vault_auth_overlay(
    runtime_id: str,
    *,
    vault_posture: dict[str, Any],
    env_keys: dict[str, str],
) -> StatusRecord | None:
    runtime_keys = vault_posture.get("runtime_keys")
    has_runtime_key = bool(isinstance(runtime_keys, dict) and runtime_keys.get(runtime_id))
    if runtime_id.startswith("cursor_") and env_keys.get("CURSOR_API_KEY"):
        has_runtime_key = True
    if runtime_id.startswith("codex_") and (
        env_keys.get("CODEX_API_KEY") or env_keys.get("OPENAI_API_KEY")
    ):
        has_runtime_key = True

    if not vault_posture.get("unlocked"):
        return {
            "logged_in": False,
            "auth_method": "vault_locked",
            "provider_label": "Vault locked",
            "vault_posture": "vault_locked",
            "message": str(vault_posture.get("hint") or "Unlock /vault to use vault-fed runtime keys."),
        }
    if has_runtime_key:
        label = "Cursor vault key" if runtime_id.startswith("cursor_") else "Codex/OpenAI vault key"
        return {
            "logged_in": True,
            "auth_method": "vault_api_key",
            "provider_label": label,
            "vault_posture": "ready",
            "message": "Authenticated via unlocked Axon-X vault.",
        }
    return {
        "logged_in": False,
        "auth_method": "vault_missing_key",
        "provider_label": "Vault missing key",
        "vault_posture": "missing_keys",
        "message": str(
            vault_posture.get("hint")
            or "Add Cursor/Codex/OpenAI secrets in /vault or sign in with the CLI."
        ),
    }


def _cursor_auth_status(binary: str, *, vault_posture: dict[str, Any], env_keys: dict[str, str], probe_env: dict[str, str] | None = None) -> StatusRecord:
    runtime_env = probe_env or {**os.environ, **env_keys}
    vault_overlay = _vault_auth_overlay("cursor_local", vault_posture=vault_posture, env_keys=env_keys)
    if not binary:
        if vault_overlay:
            return vault_overlay
        return {
            "logged_in": False,
            "auth_method": "",
            "provider_label": "Not installed",
            "vault_posture": vault_posture.get("posture"),
            "message": "Install Cursor CLI to use the interactive runtime.",
        }

    def _probe(env: dict[str, str]) -> StatusRecord:
        try:
            proc = _run_command([binary, "agent", "status"], env=env)
        except subprocess.TimeoutExpired:
            return {
                "logged_in": False,
                "auth_method": "",
                "provider_label": "Timed out",
                "vault_posture": vault_posture.get("posture"),
                "message": "Cursor auth probe timed out. Run `cursor agent status` manually.",
            }
        except Exception:
            return {
                "logged_in": False,
                "auth_method": "",
                "provider_label": "Probe failed",
                "vault_posture": vault_posture.get("posture"),
                "message": "Cursor auth probe failed. Run `cursor agent status` manually.",
            }
        raw = (proc.stdout or proc.stderr or "").strip()
        lowered = raw.lower()
        if "not logged in" in lowered or "authentication required" in lowered:
            return {
                "logged_in": False,
                "auth_method": "",
                "provider_label": "Not signed in",
                "vault_posture": vault_posture.get("posture"),
                "message": "Cursor is installed but not signed in. Run `cursor agent login` or unlock /vault.",
            }
        if proc.returncode == 0 and raw:
            return {
                "logged_in": True,
                "auth_method": "oauth",
                "provider_label": "Cursor",
                "account_label": raw.splitlines()[0].strip(),
                "vault_posture": "ready",
                "message": "Authenticated with Cursor subscription.",
            }
        return {
            "logged_in": False,
            "auth_method": "",
            "provider_label": "Not signed in",
            "vault_posture": vault_posture.get("posture"),
            "message": "Cursor is installed but not signed in. Run `cursor agent login` or unlock /vault.",
        }

    has_api_key = bool(runtime_env.get("CURSOR_API_KEY", "").strip())
    if has_api_key:
        key_source = "vault_api_key" if env_keys.get("CURSOR_API_KEY") else "api_key"
        oauth_probe = _probe(env_without_api_keys(runtime_env, family="cursor"))
        if oauth_probe.get("logged_in"):
            return {
                **oauth_probe,
                "auth_method": "oauth",
                "provider_label": "Cursor subscription",
                "message": (
                    "Cursor subscription is ready. "
                    + (
                        "CURSOR_API_KEY is also set — remove it from /vault if dispatch fails."
                        if key_source == "vault_api_key"
                        else "Unset CURSOR_API_KEY in the control-plane shell env to avoid auth conflicts."
                    )
                ),
            }

    probed = _probe(runtime_env)
    if probed.get("logged_in"):
        if has_api_key:
            key_source = "vault_api_key" if env_keys.get("CURSOR_API_KEY") else "api_key"
            return {
                "logged_in": True,
                "auth_method": key_source,
                "provider_label": "Cursor API key",
                "vault_posture": vault_posture.get("posture"),
                "message": "Authenticated via CURSOR_API_KEY"
                + (" from vault." if key_source == "vault_api_key" else "."),
            }
        return probed
    if has_api_key:
        return {
            "logged_in": False,
            "auth_method": "api_key_invalid",
            "provider_label": "Cursor API key",
            "vault_posture": vault_posture.get("posture"),
            "message": (
                "CURSOR_API_KEY is set but Cursor CLI is not signed in. "
                "Fix the vault secret, clear shell env, or run `cursor agent login`."
            ),
        }
    if vault_overlay and vault_posture.get("unlocked") and vault_overlay.get("logged_in"):
        return vault_overlay
    return probed


def _codex_auth_status(binary: str, *, vault_posture: dict[str, Any], env_keys: dict[str, str], probe_env: dict[str, str] | None = None) -> StatusRecord:
    runtime_env = probe_env or {**os.environ, **env_keys}
    if runtime_env.get("CODEX_API_KEY", "").strip() or runtime_env.get("OPENAI_API_KEY", "").strip():
        source = "vault_api_key" if (
            env_keys.get("CODEX_API_KEY") or env_keys.get("OPENAI_API_KEY")
        ) else "api_key"
        return {
            "logged_in": True,
            "auth_method": source,
            "provider_label": "OpenAI API key",
            "vault_posture": vault_posture.get("posture") if source == "vault_api_key" else "ready",
            "message": "Authenticated via Codex/OpenAI API key"
            + (" from vault." if source == "vault_api_key" else "."),
        }
    vault_overlay = _vault_auth_overlay("codex_local", vault_posture=vault_posture, env_keys=env_keys)
    if vault_overlay and vault_posture.get("unlocked") and not vault_overlay.get("logged_in"):
        if not binary:
            return vault_overlay
    if not binary:
        if vault_overlay:
            return vault_overlay
        return {
            "logged_in": False,
            "auth_method": "",
            "provider_label": "Not installed",
            "vault_posture": vault_posture.get("posture"),
            "message": "Install Codex CLI to use the automation runtime.",
        }
    try:
        proc = _run_command([binary, "login", "status"], env=runtime_env)
    except subprocess.TimeoutExpired:
        return {
            "logged_in": False,
            "auth_method": "",
            "provider_label": "Timed out",
            "vault_posture": vault_posture.get("posture"),
            "message": "Codex auth probe timed out. Run `codex login status` manually.",
        }
    except Exception:
        return {
            "logged_in": False,
            "auth_method": "",
            "provider_label": "Probe failed",
            "vault_posture": vault_posture.get("posture"),
            "message": "Codex auth probe failed. Run `codex login status` manually.",
        }
    raw = (proc.stdout or proc.stderr or "").strip()
    lowered = raw.lower()
    if proc.returncode == 0 and raw:
        method = "chatgpt" if "chatgpt" in lowered else "oauth"
        return {
            "logged_in": True,
            "auth_method": method,
            "provider_label": "Codex",
            "account_label": raw.splitlines()[0].strip(),
            "vault_posture": "ready",
            "message": "Authenticated with Codex CLI.",
        }
    if vault_overlay and vault_posture.get("unlocked"):
        return vault_overlay
    return {
        "logged_in": False,
        "auth_method": "",
        "provider_label": "Not signed in",
        "vault_posture": vault_posture.get("posture"),
        "message": "Codex is installed but not signed in. Run `codex login` or unlock /vault.",
    }


def _local_runtime_record(
    runtime_id: str,
    *,
    family: str,
    binary: str,
    auth: StatusRecord,
    label: str,
) -> StatusRecord:
    return {
        "id": runtime_id,
        "family": family,
        "label": label,
        "target_type": "local",
        "available": bool(binary),
        "binary": binary,
        "auth": auth,
        "ready": bool(binary) and bool(auth.get("logged_in")),
        "mode_support": ["ask", "plan", "agent"],
    }


def _cloud_runtime_record(
    runtime_id: str,
    *,
    family: str,
    label: str,
    vault_posture: dict[str, Any],
    env_keys: dict[str, str],
) -> StatusRecord:
    enabled = _truthy_env(os.environ.get(f"AXON_WATCH_{runtime_id.upper()}_ENABLED"))
    auth = _vault_auth_overlay(runtime_id, vault_posture=vault_posture, env_keys=env_keys) or {
        "logged_in": False,
        "auth_method": "",
        "provider_label": label,
        "vault_posture": vault_posture.get("posture"),
        "message": "Cloud runtime not configured yet in Axon-X." if not enabled else "Cloud runtime flagged as enabled.",
    }
    if enabled and auth.get("logged_in"):
        auth = {
            **auth,
            "auth_method": "vault_api_key",
            "message": "Cloud runtime enabled with vault-fed credentials.",
        }
    ready = bool(enabled) and bool(auth.get("logged_in"))
    if enabled and not auth.get("logged_in") and vault_posture.get("unlocked"):
        auth = {
            **auth,
            "message": str(
                vault_posture.get("hint")
                or "Cloud runtime enabled but vault keys are missing for this target."
            ),
        }
    return {
        "id": runtime_id,
        "family": family,
        "label": label,
        "target_type": "cloud",
        "available": enabled,
        "binary": "",
        "auth": auth,
        "ready": ready,
        "mode_support": ["ask", "plan", "agent"],
    }


def _choose_default_runtime(local: list[StatusRecord], cloud: list[StatusRecord]) -> str:
    explicit = str(os.environ.get("AXON_WATCH_IDE_RUNTIME_TARGET", "")).strip().lower()
    known = {record["id"]: record for record in [*local, *cloud]}
    if explicit in known:
        return explicit

    preferred_family = str(os.environ.get("AXON_WATCH_IDE_RUNTIME_FAMILY", "cursor")).strip().lower()
    family_order = [preferred_family, "cursor", "codex"]
    seen: set[str] = set()
    for family in family_order:
        if family in seen:
            continue
        seen.add(family)
        for record in local:
            if record["family"] == family and record["ready"]:
                return str(record["id"])
    for record in local:
        if record["available"]:
            return str(record["id"])
    return "cursor_local"


def runtime_status_snapshot(*, force_refresh: bool = False) -> StatusRecord:
    cached = _SNAPSHOT_CACHE.get("payload")
    fetched_at = float(_SNAPSHOT_CACHE.get("fetched_at") or 0.0)
    if not force_refresh and cached is not None and (time.monotonic() - fetched_at) < _CACHE_TTL_SECONDS:
        return copy.deepcopy(cached)

    context = fetch_runtime_context(force_refresh=force_refresh)
    vault_posture = dict(context.get("vault_runtime") or {})
    merged_env = dict(os.environ)
    for key, value in dict(context.get("env") or {}).items():
        if not str(merged_env.get(key, "")).strip():
            merged_env[key] = value
    vault_env_only = {
        key: value
        for key, value in merged_env.items()
        if key in {"CURSOR_API_KEY", "CODEX_API_KEY", "OPENAI_API_KEY"}
        and value
        and not str(os.environ.get(key, "")).strip()
    }

    cursor_path = find_cursor_cli(os.environ.get("AXON_WATCH_CURSOR_CLI_PATH", "").strip())
    codex_path = find_codex_cli(os.environ.get("AXON_WATCH_CODEX_CLI_PATH", "").strip())

    local = [
        _local_runtime_record(
            "cursor_local",
            family="cursor",
            binary=cursor_path,
            auth=_cursor_auth_status(
                cursor_path,
                vault_posture=vault_posture,
                env_keys=vault_env_only,
                probe_env=merged_env,
            ),
            label="Cursor CLI (local)",
        ),
        _local_runtime_record(
            "codex_local",
            family="codex",
            binary=codex_path,
            auth=_codex_auth_status(
                codex_path,
                vault_posture=vault_posture,
                env_keys=vault_env_only,
                probe_env=merged_env,
            ),
            label="Codex CLI (local)",
        ),
    ]
    cloud = [
        _cloud_runtime_record(
            "cursor_cloud",
            family="cursor",
            label="Cursor Cloud Agent",
            vault_posture=vault_posture,
            env_keys=vault_env_only,
        ),
        _cloud_runtime_record(
            "codex_cloud",
            family="codex",
            label="Codex Cloud Task",
            vault_posture=vault_posture,
            env_keys=vault_env_only,
        ),
    ]
    default_runtime = _choose_default_runtime(local, cloud)

    for record in [*local, *cloud]:
        record["recommended"] = record["id"] == default_runtime

    payload = {
        "updated_at": _utc_now_iso(),
        "default_runtime": default_runtime,
        "vault_runtime": vault_posture,
        "local": local,
        "cloud": cloud,
    }
    _SNAPSHOT_CACHE["fetched_at"] = time.monotonic()
    _SNAPSHOT_CACHE["payload"] = copy.deepcopy(payload)
    return copy.deepcopy(payload)


def runtime_identity_snapshot() -> StatusRecord:
    snapshot = runtime_status_snapshot()
    default_runtime = str(snapshot.get("default_runtime") or "")
    records = [*list(snapshot.get("local") or []), *list(snapshot.get("cloud") or [])]
    selected = next((record for record in records if record.get("id") == default_runtime), None)

    if not selected:
        return {
            "provider_family": "bootstrap",
            "provider_name": "Axon-X Bootstrap",
            "model_name": "bootstrap-model",
            "mode_default": os.environ.get("AXON_WATCH_MODE_DEFAULT", "agent"),
            "tool_calling_supported": False,
            "reasoning_supported": False,
        }

    family = str(selected.get("family") or "cursor")
    provider_name = "Cursor CLI" if family == "cursor" else "Codex CLI"
    model_name = (
        os.environ.get("AXON_WATCH_CURSOR_MODEL", "cursor-default")
        if family == "cursor"
        else os.environ.get("AXON_WATCH_CODEX_MODEL", "gpt-5.5")
    )
    if str(selected.get("target_type") or "") == "cloud":
        provider_name = "Cursor Cloud Agent" if family == "cursor" else "Codex Cloud Task"

    return {
        "provider_family": f"{family}_{selected.get('target_type')}",
        "provider_name": provider_name,
        "model_name": model_name,
        "mode_default": os.environ.get("AXON_WATCH_MODE_DEFAULT", "agent"),
        "tool_calling_supported": bool(selected.get("ready")),
        "reasoning_supported": bool(selected.get("available")),
    }
