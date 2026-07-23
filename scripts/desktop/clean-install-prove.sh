#!/usr/bin/env bash
# Prove VAXON .deb installs and starts sidecars in a clean Debian container
# with no axon-watch checkout, Node, or host Python venv.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

DEB="${1:-apps/console-desktop/src-tauri/target/release/bundle/deb/VAXON_0.1.0_amd64.deb}"
test -f "$DEB"
DEB_ABS="$(cd "$(dirname "$DEB")" && pwd)/$(basename "$DEB")"

EVIDENCE="$ROOT/docs/VAXON_DESKTOP_VERIFY_EVIDENCE.md"
IMAGE="${AXON_CLEAN_INSTALL_IMAGE:-kalilinux/kali-rolling:latest}"
NAME="vaxon-clean-install-$$"

cleanup() {
  docker rm -f "$NAME" >/dev/null 2>&1 || true
}
trap cleanup EXIT

echo "==> Clean Debian install prove ($IMAGE)"
docker pull "$IMAGE" >/dev/null

docker create --name "$NAME" \
  -e HOME=/root \
  -e AXON_WATCH_STATE_DIR=/root/.local/share/axon-watch/state \
  -e AXON_WATCH_BIND_HOST=127.0.0.1 \
  -e AXON_WATCH_WATCH_SERVICE_PORT=8788 \
  -e AXON_WATCH_CONTROL_PLANE_PORT=8787 \
  -e AXON_WATCH_CONSOLE_DIST=/usr/lib/VAXON/resources/console-web-dist \
  -e AXON_WATCH_DEPLOYMENT_MODE=desktop \
  -e AXON_WATCH_AUTH_MODE=local_token \
  -e AXON_WATCH_AUTH_ALLOW_LOOPBACK=1 \
  -e AXON_WATCH_OPERATOR_TOKEN=clean-install-prove-token \
  "$IMAGE" sleep 3600 >/dev/null

docker cp "$DEB_ABS" "$NAME:/tmp/vaxon.deb"

docker start "$NAME" >/dev/null
docker exec "$NAME" bash -lc '
  set -euo pipefail
  export DEBIAN_FRONTEND=noninteractive
  apt-get update -qq
  apt-get install -y -qq ca-certificates curl >/dev/null
  # Install package; ignore unpack configure failures from missing GUI libs by forcing deps where possible.
  apt-get install -y -qq /tmp/vaxon.deb || true
  dpkg -i --force-depends /tmp/vaxon.deb
  apt-get install -y -qq -f >/dev/null || true
  test -x /usr/bin/axon-console-desktop
  test -x /usr/bin/axon-watch-sidecar
  test -x /usr/bin/axon-control-plane-sidecar
  test -f /usr/lib/VAXON/resources/console-web-dist/index.html
  mkdir -p "$AXON_WATCH_STATE_DIR" /root/.config/axon-watch
  cat > /root/.config/axon-watch/deployment.env <<EOF
AXON_WATCH_DEPLOYMENT_MODE=desktop
AXON_WATCH_BIND_HOST=127.0.0.1
AXON_WATCH_CONTROL_PLANE_PORT=8787
AXON_WATCH_WATCH_SERVICE_PORT=8788
AXON_WATCH_STATE_DIR=$AXON_WATCH_STATE_DIR
AXON_WATCH_OPERATOR_TOKEN=clean-install-prove-token
AXON_WATCH_AUTH_MODE=local_token
AXON_WATCH_AUTH_ALLOW_LOOPBACK=1
AXON_WATCH_CONSOLE_DIST=/usr/lib/VAXON/resources/console-web-dist
EOF
  /usr/bin/axon-watch-sidecar >/tmp/watch.log 2>&1 &
  echo $! >/tmp/watch.pid
  /usr/bin/axon-control-plane-sidecar >/tmp/cp.log 2>&1 &
  echo $! >/tmp/cp.pid
  for i in $(seq 1 60); do
    if curl -fsS http://127.0.0.1:8787/api/health >/dev/null 2>&1; then
      echo "clean_install_health_ok"
      curl -fsS http://127.0.0.1:8787/api/health
      exit 0
    fi
    sleep 1
  done
  echo "clean_install_health_failed" >&2
  echo "--- watch ---"; tail -50 /tmp/watch.log || true
  echo "--- cp ---"; tail -50 /tmp/cp.log || true
  exit 1
'

STATUS=0
RESULT="$(docker exec "$NAME" bash -lc 'curl -fsS http://127.0.0.1:8787/api/health' 2>/dev/null)" || STATUS=$?

{
  echo
  echo "## Clean Debian container install ($(date -u +%Y-%m-%dT%H:%MZ))"
  echo
  if [[ "$STATUS" -eq 0 ]]; then
    echo "**Result: PASS**"
    echo
    echo "- Image: \`$IMAGE\` (no axon-watch checkout / Node / host venv inside container)"
    echo "- Installed: \`$(basename "$DEB_ABS")\`"
    echo "- Binaries present: \`axon-console-desktop\`, both sidecars, \`console-web-dist/index.html\`"
    echo "- Sidecars started; Control Plane \`/api/health\` responded:"
    echo
    echo '```json'
    echo "$RESULT" | python3 -m json.tool 2>/dev/null || echo "$RESULT"
    echo '```'
    echo
    echo "Note: full GTK/WebKitGTK GUI launch inside the container was not required for this gate;"
    echo "this proves the packaged binaries run without the development checkout."
  else
    echo "**Result: FAIL** — see script output; health check did not succeed."
  fi
} >>"$EVIDENCE"

if [[ "$STATUS" -ne 0 ]]; then
  echo "clean-install prove FAILED" >&2
  exit 1
fi

echo "clean_install_prove_ok"
