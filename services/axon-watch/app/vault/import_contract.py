"""Allowlisted keys accepted by the monitor credential import."""

from __future__ import annotations

ALLOWED_IMPORT_KEYS: tuple[str, ...] = (
    "SENTRY_AUTH_TOKEN",
    "SENTRY_API_TOKEN",
    "SENTRY_ORG_SLUG",
    "SENTRY_PROJECT_SLUG",
    "POSTHOG_PERSONAL_API_KEY",
    "DASHPRO_POSTHOG_PROJECT_ID",
    "EXPO_PUBLIC_POSTHOG_KEY",
    "EXPO_PUBLIC_POSTHOG_HOST",
    "EXPO_PUBLIC_SENTRY_DSN",
    "AXON_WATCH_GOOGLE_CSE_API_KEY",
    "AXON_WATCH_GOOGLE_CSE_CX",
    "AXON_WATCH_SEARXNG_URL",
    # Authenticated GitHub API health probes (avoids IP 60/hr false alarms).
    "GH_TOKEN",
    "GITHUB_TOKEN",
    "AXON_GITHUB_TOKEN",
    # Supabase CLI access for read-only migration history checks and separately
    # operator-approved db push operations.
    "SUPABASE_ACCESS_TOKEN",
    # Optional CLI runtime API keys (subscription login preferred).
    "CURSOR_API_KEY",
    "ANTHROPIC_API_KEY",
    "CODEX_API_KEY",
    "OPENAI_API_KEY",
)
