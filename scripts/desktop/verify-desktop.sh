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
  else
    echo "No .deb yet — run scripts/desktop/build-portable-deb.sh"
  fi
else
  echo "No bundle dir yet — run scripts/desktop/build-portable-deb.sh"
fi

echo "verify:desktop OK"
