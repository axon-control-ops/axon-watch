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
)
