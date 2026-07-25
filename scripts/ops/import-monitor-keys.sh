#!/usr/bin/env bash
# Import DashPro monitor credentials into Axon vault for live Sentry/PostHog signals (OP-B4).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

if [[ -f .env.local ]]; then
  set -a
  # shellcheck disable=SC1091
  source .env.local
  set +a
fi

: "${SENTRY_AUTH_TOKEN:?Set SENTRY_AUTH_TOKEN in the environment or .env.local}"
: "${POSTHOG_PERSONAL_API_KEY:?Set POSTHOG_PERSONAL_API_KEY in the environment or .env.local}"
: "${DASHPRO_POSTHOG_PROJECT_ID:?Set DASHPRO_POSTHOG_PROJECT_ID in the environment or .env.local}"

echo "Importing monitor keys via control-plane vault (requires unlocked vault)…"
curl -fsS -X POST "http://127.0.0.1:8787/api/vault/import/monitor-keys" \
  -H 'Content-Type: application/json' \
  -d "$(python3 - <<'PY'
import json, os
print(json.dumps({
  "SENTRY_AUTH_TOKEN": os.environ["SENTRY_AUTH_TOKEN"],
  "POSTHOG_PERSONAL_API_KEY": os.environ["POSTHOG_PERSONAL_API_KEY"],
  "DASHPRO_POSTHOG_PROJECT_ID": os.environ["DASHPRO_POSTHOG_PROJECT_ID"],
}))
PY
)" | python3 -m json.tool

echo "Verify monitor probes: npm run verify:dashpro-monitors"
