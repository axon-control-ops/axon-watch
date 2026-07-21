#!/usr/bin/env bash
# Verify desktop packaging contracts, unit tests, and deb artifact shape.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

if [[ -f "$HOME/.cargo/env" ]]; then
  # shellcheck disable=SC1091
  source "$HOME/.cargo/env"
fi
export PATH="${HOME}/.cargo/bin:${PATH}"

echo "==> Frontend desktop tests"
npm run test -w @axon-watch/console-web -- --run \
  src/lib/desktop-capability.test.ts \
  src/lib/kairo-audio-unlock.test.ts \
  src/lib/kairo-voice-playback.test.ts \
  src/lib/galaxy-panel-widths.test.ts \
  src/features/voice-deck/voice-deck.test.ts \
  src/features/host-context/motion-orchestrator.test.ts

echo "==> Host + desktop Python tests"
./scripts/dev/python.sh -m unittest \
  tests.test_host_context \
  tests.test_host_reminders \
  tests.test_host_policy_parity \
  tests.test_desktop_session

echo "==> Rust desktop tests"
(
  cd apps/console-desktop/src-tauri
  cargo test
)

echo "==> Deb artifact checks"
DEB_DIR="apps/console-desktop/src-tauri/target/release/bundle/deb"
if [[ -d "$DEB_DIR" ]]; then
  DEB="$(ls -1 "$DEB_DIR"/*.deb 2>/dev/null | head -n1 || true)"
  if [[ -n "${DEB:-}" ]]; then
    echo "Found $DEB"
    dpkg-deb -I "$DEB" | rg -n 'Package:|Version:|Depends:|Architecture:'
    LISTING="$(mktemp)"
    dpkg-deb -c "$DEB" >"$LISTING"
    if ! rg -q 'axon-watch-sidecar' "$LISTING"; then
      echo "ERROR: .deb missing axon-watch-sidecar externalBin" >&2
      exit 1
    fi
    if ! rg -q 'axon-control-plane-sidecar' "$LISTING"; then
      echo "ERROR: .deb missing axon-control-plane-sidecar externalBin" >&2
      exit 1
    fi
    if ! rg -q 'console-web-dist/index\.html' "$LISTING"; then
      echo "ERROR: .deb missing console-web-dist/index.html resource" >&2
      exit 1
    fi
    SIZE_BYTES="$(stat -c%s "$DEB")"
    if (( SIZE_BYTES < 30000000 )); then
      echo "ERROR: .deb is only ${SIZE_BYTES} bytes — sidecars likely missing (expect >30MB)" >&2
      exit 1
    fi
    echo "Deb contains SPA + both sidecars (${SIZE_BYTES} bytes)"
  else
    echo "No .deb yet — run scripts/desktop/build-portable-deb.sh"
    exit 1
  fi
else
  echo "No bundle dir yet — run scripts/desktop/build-portable-deb.sh"
  exit 1
fi

echo "verify:desktop OK"
