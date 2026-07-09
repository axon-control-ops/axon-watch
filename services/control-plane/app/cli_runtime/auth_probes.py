"""CLI auth probe helpers for local Cursor/Codex runtime status."""

from __future__ import annotations

import os
import subprocess
from typing import Any

from app.cli_runtime.runtime_auth import env_without_api_keys

StatusRecord = dict[str, Any]

# `cursor agent status` commonly takes 6–8s on this host; keep headroom above that.
_AUTH_PROBE_TIMEOUT_SECONDS = 15


def _run_command(
    parts: list[str],
    *,
    timeout: int = _AUTH_PROBE_TIMEOUT_SECONDS,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        parts,
        capture_output=True,
        text=True,
        timeout=timeout,
        env=env or {**os.environ, "NO_COLOR": "1"},
    )


def vault_auth_overlay(
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


def cursor_auth_status(
    binary: str,
    *,
    vault_posture: dict[str, Any],
    env_keys: dict[str, str],
    probe_env: dict[str, str] | None = None,
) -> StatusRecord:
    runtime_env = probe_env or {**os.environ, **env_keys}
    vault_overlay = vault_auth_overlay("cursor_local", vault_posture=vault_posture, env_keys=env_keys)
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


def codex_auth_status(
    binary: str,
    *,
    vault_posture: dict[str, Any],
    env_keys: dict[str, str],
    probe_env: dict[str, str] | None = None,
) -> StatusRecord:
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
    vault_overlay = vault_auth_overlay("codex_local", vault_posture=vault_posture, env_keys=env_keys)
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


# Private aliases kept for callers that historically imported underscored names.
_vault_auth_overlay = vault_auth_overlay
_cursor_auth_status = cursor_auth_status
_codex_auth_status = codex_auth_status
