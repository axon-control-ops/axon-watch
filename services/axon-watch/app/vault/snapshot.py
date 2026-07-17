"""Operator-facing vault snapshot with consumer readiness (no secret values)."""

from __future__ import annotations

from pathlib import Path

from app.vault.cli_runtime_probe import probe_codex_cli_subscription, probe_cursor_cli_subscription
from app.vault.credential_resolver import merge_monitor_env, vault_status
from app.vault.import_contract import ALLOWED_IMPORT_KEYS

_VAULT_CONSUMERS: tuple[dict[str, object], ...] = (
    {
        "id": "dashpro_sentry",
        "label": "DashPro Sentry monitor",
        "required_keys": ("SENTRY_AUTH_TOKEN",),
        "optional_keys": ("SENTRY_API_TOKEN", "SENTRY_ORG_SLUG", "SENTRY_PROJECT_SLUG", "EXPO_PUBLIC_SENTRY_DSN"),
        "auth_note": (
            "Read monitors need project:read (or event:read). "
            "Resolving issues from Axon requires event:write or project:write on the same token."
        ),
    },
    {
        "id": "dashpro_posthog",
        "label": "DashPro PostHog monitor",
        "required_keys": ("POSTHOG_PERSONAL_API_KEY", "DASHPRO_POSTHOG_PROJECT_ID"),
        "optional_keys": ("EXPO_PUBLIC_POSTHOG_KEY", "EXPO_PUBLIC_POSTHOG_HOST"),
    },
    {
        "id": "cursor_runtime",
        "label": "Cursor CLI runtime",
        "optional_keys": ("CURSOR_API_KEY",),
        "subscription_probe": "cursor",
        "auth_note": (
            "Pro/Team: sign in on the host with `cursor agent login` (browser flow). "
            "Optional: CURSOR_API_KEY in /vault for CI/headless only."
        ),
    },
    {
        "id": "codex_runtime",
        "label": "Codex CLI runtime",
        "any_of_keys": ("CODEX_API_KEY", "OPENAI_API_KEY"),
        "subscription_probe": "codex",
        "auth_note": "Use `codex login`, or store CODEX_API_KEY / OPENAI_API_KEY in /vault.",
    },
    {
        "id": "openai_provider",
        "label": "OpenAI provider fallback",
        "required_keys": ("OPENAI_API_KEY",),
    },
    {
        "id": "kairo_tts",
        "label": "KAIRO Azure speech playback",
        "required_keys": ("AZURE_SPEECH_KEY",),
        "optional_keys": ("AZURE_SPEECH_REGION", "azure_speech_key", "azure_speech_region"),
        "auth_note": "Store AZURE_SPEECH_KEY (or azure_speech_key) and optional region in /vault.",
    },
    {
        "id": "vaxon_research",
        "label": "VAXON online research (Google CSE)",
        "required_keys": ("AXON_WATCH_GOOGLE_CSE_API_KEY", "AXON_WATCH_GOOGLE_CSE_CX"),
        "optional_keys": (
            "GOOGLE_SEARCH_API_KEY",
            "GOOGLE_CSE_ID",
            "EXPO_PUBLIC_GOOGLE_CSE_API_KEY",
            "EXPO_PUBLIC_GOOGLE_CSE_CX",
            "google_cse_api_key",
            "google_cse_cx",
        ),
        "auth_note": (
            "Store AXON_WATCH_GOOGLE_CSE_API_KEY and AXON_WATCH_GOOGLE_CSE_CX in /vault "
            "(password field holds the value). Unlock vault before research runs."
        ),
    },
    {
        "id": "vaxon_searxng",
        "label": "VAXON online research (SearXNG)",
        "required_keys": ("AXON_WATCH_SEARXNG_URL",),
        "auth_note": (
            "Store AXON_WATCH_SEARXNG_URL in /vault (password field), e.g. "
            "http://127.0.0.1:8080. SearXNG is preferred over Google when set."
        ),
    },
)


def _keys_present(env: dict[str, str], keys: tuple[str, ...]) -> list[str]:
    return [name for name in keys if str(env.get(name, "")).strip()]


def _subscription_probe(probe_name: str) -> dict[str, object]:
    if probe_name == "cursor":
        return probe_cursor_cli_subscription()
    if probe_name == "codex":
        return probe_codex_cli_subscription()
    return {"installed": False, "logged_in": False, "account_label": "", "message": ""}


def _consumer_record(env: dict[str, str], spec: dict[str, object]) -> dict[str, object]:
    required = tuple(str(key) for key in spec.get("required_keys") or ())
    optional = tuple(str(key) for key in spec.get("optional_keys") or ())
    any_of = tuple(str(key) for key in spec.get("any_of_keys") or ())
    subscription_probe = str(spec.get("subscription_probe") or "").strip()
    auth_note = str(spec.get("auth_note") or "").strip()

    satisfied_required = _keys_present(env, required)
    missing_required = [name for name in required if name not in satisfied_required]
    satisfied_optional = _keys_present(env, optional)
    satisfied_any = _keys_present(env, any_of)

    subscription: dict[str, object] = {}
    subscription_satisfied: list[str] = []
    if subscription_probe:
        subscription = _subscription_probe(subscription_probe)
        if subscription.get("logged_in"):
            account = str(subscription.get("account_label") or "").strip()
            subscription_satisfied.append(
                f"cli_subscription:{account}" if account else "cli_subscription"
            )

    alternative_satisfied = not any_of or bool(satisfied_any)
    key_ready = not missing_required and alternative_satisfied and (
        bool(satisfied_required) or bool(satisfied_optional) or bool(satisfied_any)
    )
    subscription_ready = bool(subscription_satisfied)

    if subscription_ready or key_ready:
        status = "ready"
    elif satisfied_required or satisfied_optional or satisfied_any or subscription.get("installed"):
        status = "partial"
    else:
        status = "missing"

    if subscription_probe and not subscription_ready and not key_ready:
        if not missing_required and not any_of:
            missing_required = ["subscription_or_api_key"]
        elif any_of and not satisfied_any:
            missing_required.append(f"one_of:{'|'.join(any_of)}")

    return {
        "id": str(spec.get("id") or ""),
        "label": str(spec.get("label") or ""),
        "status": status,
        "required_keys": list(required),
        "optional_keys": list(optional),
        "any_of_keys": list(any_of),
        "satisfied_keys": satisfied_required + satisfied_optional + satisfied_any + subscription_satisfied,
        "missing_keys": missing_required,
        "auth_note": auth_note,
        "subscription_auth": subscription if subscription_probe else None,
        "vault_surface": "/vault",
    }


def vault_operator_snapshot(*, project_root: Path | None = None) -> dict[str, object]:
    env = merge_monitor_env(project_root=project_root)
    base = vault_status(project_root=project_root)
    consumers = [_consumer_record(env, spec) for spec in _VAULT_CONSUMERS]
    return {
        **base,
        "consumers": consumers,
        "known_keys": list(ALLOWED_IMPORT_KEYS),
        "import_hint": (
            "Import named monitor keys via POST /api/vault/import or "
            "scripts/ops/import-vault-from-signal.py. Secret values are never returned by the API."
        ),
    }
