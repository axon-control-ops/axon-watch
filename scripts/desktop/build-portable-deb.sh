#!/usr/bin/env bash
# Build a portable VAXON .deb for Debian/Kali/Ubuntu x86_64.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

if [[ -f "$HOME/.cargo/env" ]]; then
  # shellcheck disable=SC1091
  source "$HOME/.cargo/env"
fi
export PATH="${HOME}/.cargo/bin:${PATH}"
export WEBKIT_DISABLE_DMABUF_RENDERER="${WEBKIT_DISABLE_DMABUF_RENDERER:-1}"
export AXON_DESKTOP_PACKAGED=1
export AXON_WATCH_REPO_ROOT="$ROOT"

echo "==> Building console-web dist"
npm run build -w @axon-watch/console-web

echo "==> Building Python sidecars (optional if PyInstaller available)"
if [[ "${AXON_DESKTOP_SKIP_SIDECARS:-0}" == "1" ]]; then
  echo "Skipping sidecar freeze (AXON_DESKTOP_SKIP_SIDECARS=1)"
elif ./scripts/desktop/build-python-sidecars.sh; then
  echo "Sidecars ready"
else
  echo "WARNING: sidecar freeze failed — packaged app will fall back to system/repo Python" >&2
fi

# Copy sidecars next to resources if present
SIDECAR_DIR="$ROOT/apps/console-desktop/src-tauri/binaries"
RESOURCE_SIDECARS="$ROOT/apps/console-desktop/src-tauri/resources/sidecars"
if [[ -d "$SIDECAR_DIR" ]]; then
  mkdir -p "$RESOURCE_SIDECARS"
  cp -f "$SIDECAR_DIR"/axon-*-sidecar-* "$RESOURCE_SIDECARS/" 2>/dev/null || true
fi

echo "==> Building Tauri .deb"
npm run tauri -w @axon-watch/console-desktop -- build --bundles deb

DEB="$(ls -1 "$ROOT/apps/console-desktop/src-tauri/target/release/bundle/deb/"*.deb | head -n1)"
echo "Built: $DEB"
ls -lh "$DEB"
