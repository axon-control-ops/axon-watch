#!/usr/bin/env bash
# Freeze Watch + Control Plane sidecars for Tauri externalBin on Linux x86_64.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

TRIPLE="${AXON_DESKTOP_TARGET_TRIPLE:-x86_64-unknown-linux-gnu}"
OUT_DIR="${AXON_DESKTOP_SIDECAR_OUT:-$ROOT/apps/console-desktop/src-tauri/binaries}"
PYTHON="${AXON_WATCH_PYTHON:-$ROOT/.venv/bin/python3}"
if [[ ! -x "$PYTHON" ]]; then
  PYTHON="$(command -v python3)"
fi

mkdir -p "$OUT_DIR"

if ! "$PYTHON" -c 'import PyInstaller' 2>/dev/null; then
  echo "Installing PyInstaller into $PYTHON ..."
  "$PYTHON" -m pip install --quiet 'pyinstaller>=6.3,<7'
fi

# Ensure editable services are importable for analysis.
"$PYTHON" -m pip install --quiet -e "$ROOT/services/axon-watch" -e "$ROOT/services/control-plane"

build_one() {
  local name="$1"
  local entry="$2"
  local service_root="$3"
  local work="$ROOT/.local/desktop-sidecar/$name"
  rm -rf "$work"
  mkdir -p "$work"
  echo "Building sidecar: $name (PYTHONPATH=$service_root)"
  PYTHONPATH="$service_root${PYTHONPATH:+:$PYTHONPATH}" "$PYTHON" -m PyInstaller \
    --noconfirm \
    --clean \
    --onefile \
    --name "$name" \
    --distpath "$work/dist" \
    --workpath "$work/build" \
    --specpath "$work" \
    --paths "$service_root" \
    --collect-submodules app \
    --hidden-import uvicorn \
    --hidden-import uvicorn.logging \
    --hidden-import uvicorn.loops \
    --hidden-import uvicorn.loops.auto \
    --hidden-import uvicorn.protocols \
    --hidden-import uvicorn.protocols.http \
    --hidden-import uvicorn.protocols.http.auto \
    --hidden-import uvicorn.protocols.websockets \
    --hidden-import uvicorn.protocols.websockets.auto \
    --hidden-import uvicorn.lifespan \
    --hidden-import uvicorn.lifespan.on \
    --hidden-import fastapi \
    --hidden-import multipart \
    --hidden-import websockets \
    --hidden-import pydantic \
    --hidden-import starlette \
    "$entry"
  local dest="$OUT_DIR/${name}-${TRIPLE}"
  cp "$work/dist/$name" "$dest"
  chmod +x "$dest"
  echo "Wrote $dest"
}

build_one "axon-watch-sidecar" "$ROOT/scripts/desktop/sidecar_axon_watch.py" "$ROOT/services/axon-watch"
build_one "axon-control-plane-sidecar" "$ROOT/scripts/desktop/sidecar_control_plane.py" "$ROOT/services/control-plane"

echo "Sidecar build complete → $OUT_DIR"
ls -la "$OUT_DIR"
