#!/usr/bin/env bash
# Launch VAXON desktop (packaged release preferred; debug/dev fallback).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

if [[ -f "$HOME/.cargo/env" ]]; then
  # shellcheck disable=SC1091
  source "$HOME/.cargo/env"
fi
export PATH="${HOME}/.cargo/bin:${PATH}"
export WEBKIT_DISABLE_DMABUF_RENDERER="${WEBKIT_DISABLE_DMABUF_RENDERER:-1}"
export AXON_WATCH_REPO_ROOT="${AXON_WATCH_REPO_ROOT:-$ROOT}"

RELEASE_BIN="$ROOT/apps/console-desktop/src-tauri/target/release/axon-console-desktop"
DEBUG_BIN="$ROOT/apps/console-desktop/src-tauri/target/debug/axon-console-desktop"
SYSTEM_BIN="$(command -v axon-console-desktop || true)"
DEV_URL="${AXON_X_DEV_URL:-http://127.0.0.1:4173}"

# Prefer an installed system binary (from .deb).
if [[ -n "$SYSTEM_BIN" && -x "$SYSTEM_BIN" ]]; then
  export AXON_DESKTOP_PACKAGED="${AXON_DESKTOP_PACKAGED:-1}"
  export AXON_DESKTOP_SPAWN_SIDECARS="${AXON_DESKTOP_SPAWN_SIDECARS:-1}"
  exec "$SYSTEM_BIN"
fi

if [[ -x "$RELEASE_BIN" ]]; then
  # Release builds embed dist; spawn local sidecars when packaging env is set.
  export AXON_DESKTOP_PACKAGED="${AXON_DESKTOP_PACKAGED:-0}"
  export AXON_WATCH_CONSOLE_DIST="${AXON_WATCH_CONSOLE_DIST:-$ROOT/apps/console-web/dist}"
  if [[ "${AXON_DESKTOP_SPAWN_SIDECARS:-0}" == "1" ]]; then
    exec "$RELEASE_BIN"
  fi
fi

# Dev shell against live :4173 (browser-compatible path).
if ! curl -fsS --max-time 1 "$DEV_URL" >/dev/null 2>&1; then
  echo "Axon-X: console-web not reachable at $DEV_URL" >&2
  echo "Start it first (e.g. npm run dev:console-web or scripts/dev/up.sh)." >&2
  echo "Or build a packaged app: ./scripts/desktop/build-portable-deb.sh" >&2
  notify-send --app-name="Axon-X" "Axon-X" "Console not running on ${DEV_URL}." 2>/dev/null || true
  exit 1
fi

if [[ -x "$DEBUG_BIN" ]]; then
  exec "$DEBUG_BIN"
fi

if [[ -x "$RELEASE_BIN" ]]; then
  exec "$RELEASE_BIN"
fi

exec npm run dev:console-desktop
