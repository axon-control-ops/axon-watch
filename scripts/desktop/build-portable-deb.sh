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

echo "==> Staging SPA into Tauri resources/console-web-dist"
RESOURCE_DIST="$ROOT/apps/console-desktop/src-tauri/resources/console-web-dist"
mkdir -p "$RESOURCE_DIST"
rsync -a --delete "$ROOT/apps/console-web/dist/" "$RESOURCE_DIST/"
test -f "$RESOURCE_DIST/index.html"

echo "==> Building Python sidecars"
if [[ "${AXON_DESKTOP_SKIP_SIDECARS:-0}" == "1" ]]; then
  echo "ERROR: AXON_DESKTOP_SKIP_SIDECARS=1 is not allowed for portable builds" >&2
  echo "Unset it and ensure PyInstaller can freeze Watch + Control Plane." >&2
  exit 1
fi
./scripts/desktop/build-python-sidecars.sh

SIDECAR_DIR="$ROOT/apps/console-desktop/src-tauri/binaries"
TRIPLE="${AXON_DESKTOP_TARGET_TRIPLE:-x86_64-unknown-linux-gnu}"
for name in axon-watch-sidecar axon-control-plane-sidecar; do
  if [[ ! -x "$SIDECAR_DIR/${name}-${TRIPLE}" ]]; then
    echo "ERROR: missing sidecar binary $SIDECAR_DIR/${name}-${TRIPLE}" >&2
    exit 1
  fi
done

echo "==> Building Tauri .deb"
npm run tauri -w @axon-watch/console-desktop -- build --bundles deb

DEB="$(ls -1 "$ROOT/apps/console-desktop/src-tauri/target/release/bundle/deb/"*.deb | head -n1)"
echo "Built: $DEB"
ls -lh "$DEB"
