"""CLI auth probe helpers for local Cursor/Codex/Claude runtime status."""

from __future__ import annotations

import json
import os
import subprocess
import base64
from pathlib import Path
from typing import Any

from app.cli_runtime.catalog_discovery import cursor_cli_argv
from app.cli_runtime.runtime_auth import env_without_api_keys
from app.cli_runtime.runtime_profiles import codex_profile_env

StatusRecord = dict[str, Any]


def _codex_account_email(env: dict[str, str] | None = None) -> str:
    """Return only the local Codex ID-token email claim; never expose its token."""
    try:
        runtime_env = codex_profile_env(env)
        with open(Path(runtime_env["CODEX_HOME"]) / "auth.json", encoding="utf-8") as handle:
            token = str((json.load(handle).get("tokens") or {}).get("id_token") or "")
        payload = token.split(".")[1]
        decoded = base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4))
        email = str((json.loads(decoded).get("email") or "")).strip()
        return email if "@" in email else ""
    except (OSError, ValueError, IndexError, KeyError, TypeError, json.JSONDecodeError):
        return ""

# `cursor agent status` commonly takes 6–8s on this host; keep headroom above that.
# Occasional cold starts / contention can push past 15s — retry once before failing.
_AUTH_PROBE_TIMEOUT_SECONDS = 20
_AUTH_PROBE_RETRY_TIMEOUT_SECONDS = 30


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


def _run_command_with_timeout_retry(
    parts: list[str],
    *,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    try:
        return _run_command(parts, timeout=_AUTH_PROBE_TIMEOUT_SECONDS, env=env)
    except subprocess.TimeoutExpired:
        # One longer retry — clears most false "auth timed out" flaps without
        # blocking the operator UI forever (SWR callers still use the cache).
        return _run_command(parts, timeout=_AUTH_PROBE_RETRY_TIMEOUT_SECONDS, env=env)


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
    if runtime_id.startswith("claude_") and env_keys.get("ANTHROPIC_API_KEY"):
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
        if runtime_id.startswith("cursor_"):
            label = "Cursor vault key"
        elif runtime_id.startswith("claude_"):
            label = "Anthropic vault key"
        else:
            label = "Codex/OpenAI vault key"
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
            or "Add Cursor/Codex/Claude/OpenAI secrets in /vault or sign in with the CLI."
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
        status_argv = cursor_cli_argv(binary, "status")
        try:
            proc = _run_command_with_timeout_retry(status_argv, env=env)
        except subprocess.TimeoutExpired:
            preview = " ".join(status_argv)
            return {
                "logged_in": False,
                "auth_method": "",
                "provider_label": "Timed out",
                "vault_posture": vault_posture.get("posture"),
                "message": f"Cursor auth probe timed out. Run `{preview}` manually.",
            }
        except Exception:
            preview = " ".join(status_argv)
            return {
                "logged_in": False,
                "auth_method": "",
                "provider_label": "Probe failed",
                "vault_posture": vault_posture.get("posture"),
                "message": f"Cursor auth probe failed. Run `{preview}` manually.",
            }
        raw = (proc.stdout or proc.stderr or "").strip()
        lowered = raw.lower()
        login_hint = " ".join(cursor_cli_argv(binary, "login"))
        if "not logged in" in lowered or "authentication required" in lowered:
            return {
                "logged_in": False,
                "auth_method": "",
                "provider_label": "Not signed in",
                "vault_posture": vault_posture.get("posture"),
                "message": f"Cursor is installed but not signed in. Run `{login_hint}` or unlock /vault.",
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
            "message": f"Cursor is installed but not signed in. Run `{login_hint}` or unlock /vault.",
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
                f"Fix the vault secret, clear shell env, or run `{' '.join(cursor_cli_argv(binary, 'login'))}`."
            ),
        }
    if vault_overlay and vault_posture.get("unlocked") and vault_overlay.get("logged_in"):
        return vault_overlay
    return probed


def _probe_codex_cli(
    binary: str,
    env: dict[str, str],
    *,
    vault_posture: dict[str, Any],
) -> StatusRecord | None:
    """Run `codex login status`. Returns None only on a probe/timeout error."""
    try:
        proc = _run_command_with_timeout_retry([binary, "login", "status"], env=env)
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
    if proc.returncode != 0 or not raw:
        return None
    method = "chatgpt" if "chatgpt" in lowered else "oauth"
    return {
        "logged_in": True,
        "auth_method": method,
        "provider_label": "Codex",
        "account_label": _codex_account_email(env) or raw.splitlines()[0].strip(),
        "vault_posture": "ready",
        "message": "Authenticated with Codex CLI.",
    }


def codex_auth_status(
    binary: str,
    *,
    vault_posture: dict[str, Any],
    env_keys: dict[str, str],
    probe_env: dict[str, str] | None = None,
) -> StatusRecord:
    runtime_env = codex_profile_env(probe_env or {**os.environ, **env_keys})
    vault_overlay = vault_auth_overlay("codex_local", vault_posture=vault_posture, env_keys=env_keys)
    has_api_key = bool(
        runtime_env.get("CODEX_API_KEY", "").strip() or runtime_env.get("OPENAI_API_KEY", "").strip()
    )

    if has_api_key and binary:
        # A logged-in ChatGPT/Codex subscription beats a vault/shell API key
        # that may be invalid or out of credits — probe with the key stripped
        # and prefer it if ready (mirrors claude_auth_status).
        oauth_probe = _probe_codex_cli(
            binary, env_without_api_keys(runtime_env, family="codex"), vault_posture=vault_posture
        )
        if oauth_probe and oauth_probe.get("logged_in"):
            key_source = "vault_api_key" if (
                env_keys.get("CODEX_API_KEY") or env_keys.get("OPENAI_API_KEY")
            ) else "api_key"
            return {
                **oauth_probe,
                "auth_method": "chatgpt",
                "provider_label": "Codex / ChatGPT subscription",
                "message": (
                    "Codex ChatGPT subscription is ready. "
                    + (
                        "A Codex/OpenAI key is also set in /vault and will be ignored for this session."
                        if key_source == "vault_api_key"
                        else "A Codex/OpenAI key is also set in the control-plane environment and will be ignored for this session."
                    )
                ),
            }

    if has_api_key:
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
    probed = _probe_codex_cli(binary, runtime_env, vault_posture=vault_posture)
    if probed and probed.get("logged_in"):
        return probed
    if vault_overlay and vault_posture.get("unlocked"):
        return vault_overlay
    return {
        "logged_in": False,
        "auth_method": "",
        "provider_label": "Not signed in",
        "vault_posture": vault_posture.get("posture"),
        "message": "Codex is installed but not signed in. Run `codex login` or unlock /vault.",
    }


def _probe_claude_cli(
    binary: str,
    env: dict[str, str],
    *,
    vault_posture: dict[str, Any],
) -> StatusRecord | None:
    """Run `claude auth status --json`. Returns None only on a probe/timeout error."""
    try:
        proc = _run_command_with_timeout_retry(
            [binary, "auth", "status", "--json"],
            env=env,
        )
    except subprocess.TimeoutExpired:
        return {
            "logged_in": False,
            "auth_method": "",
            "provider_label": "Timed out",
            "vault_posture": vault_posture.get("posture"),
            "message": "Claude auth probe timed out. Run `claude auth status` manually.",
        }
    except Exception:
        return {
            "logged_in": False,
            "auth_method": "",
            "provider_label": "Probe failed",
            "vault_posture": vault_posture.get("posture"),
            "message": "Claude auth probe failed. Run `claude auth status` manually.",
        }
    raw = (proc.stdout or proc.stderr or "").strip()
    payload: dict[str, Any] = {}
    if raw:
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, dict):
                payload = parsed
        except json.JSONDecodeError:
            payload = {}
    logged_in = bool(payload.get("loggedIn")) if payload else (
        proc.returncode == 0 and "logged in" in raw.lower()
    )
    if not logged_in:
        return None
    email = str(payload.get("email") or "").strip()
    org = str(payload.get("orgName") or "").strip()
    auth_method = str(payload.get("authMethod") or "oauth").strip() or "oauth"
    account = email or org or (raw.splitlines()[0].strip() if raw else "")
    subscription = str(payload.get("subscriptionType") or "").strip()
    message = "Authenticated with Claude Code CLI."
    if subscription:
        message = f"Authenticated with Claude {subscription} subscription."
    return {
        "logged_in": True,
        "auth_method": auth_method if auth_method != "claude.ai" else "oauth",
        "provider_label": "Claude",
        "account_label": account,
        "vault_posture": "ready",
        "message": message,
    }


def claude_auth_status(
    binary: str,
    *,
    vault_posture: dict[str, Any],
    env_keys: dict[str, str],
    probe_env: dict[str, str] | None = None,
) -> StatusRecord:
    runtime_env = probe_env or {**os.environ, **env_keys}
    vault_overlay = vault_auth_overlay("claude_local", vault_posture=vault_posture, env_keys=env_keys)
    has_api_key = bool(runtime_env.get("ANTHROPIC_API_KEY", "").strip())

    if has_api_key and binary:
        # A logged-in subscription beats a vault/shell API key that may be
        # out of credits — probe with the key stripped and prefer it if ready
        # (mirrors cursor_auth_status; claude_dispatch_env only strips the key
        # from the dispatch env when this reports auth_method oauth/claude.ai).
        oauth_probe = _probe_claude_cli(
            binary, env_without_api_keys(runtime_env, family="claude"), vault_posture=vault_posture
        )
        if oauth_probe and oauth_probe.get("logged_in"):
            return oauth_probe

    if has_api_key:
        source = "vault_api_key" if env_keys.get("ANTHROPIC_API_KEY") else "api_key"
        return {
            "logged_in": True,
            "auth_method": source,
            "provider_label": "Anthropic API key",
            "vault_posture": vault_posture.get("posture") if source == "vault_api_key" else "ready",
            "message": "Authenticated via ANTHROPIC_API_KEY"
            + (" from vault." if source == "vault_api_key" else "."),
        }
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
            "message": "Install Claude Code CLI to use the Claude runtime.",
        }
    probed = _probe_claude_cli(binary, runtime_env, vault_posture=vault_posture)
    if probed and probed.get("logged_in"):
        return probed
    if vault_overlay and vault_posture.get("unlocked"):
        return vault_overlay
    return {
        "logged_in": False,
        "auth_method": "",
        "provider_label": "Not signed in",
        "vault_posture": vault_posture.get("posture"),
        "message": "Claude is installed but not signed in. Run `claude auth login` or unlock /vault.",
    }


# Private aliases kept for callers that historically imported underscored names.
_vault_auth_overlay = vault_auth_overlay
_cursor_auth_status = cursor_auth_status
_codex_auth_status = codex_auth_status
_claude_auth_status = claude_auth_status
