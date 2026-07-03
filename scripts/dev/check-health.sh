#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

if [[ -f "${repo_root}/.env" ]]; then
  # shellcheck disable=SC1091
  source "${repo_root}/.env"
else
  # shellcheck disable=SC1091
  source "${repo_root}/.env.example"
fi

: "${AXON_WATCH_CONTROL_PLANE_PORT:=8787}"
: "${AXON_WATCH_WATCH_SERVICE_PORT:=8788}"

echo "Control plane health:"
curl -fsS "http://127.0.0.1:${AXON_WATCH_CONTROL_PLANE_PORT}/api/health"
echo
echo "Control plane readiness:"
curl -fsS "http://127.0.0.1:${AXON_WATCH_CONTROL_PLANE_PORT}/api/readiness"
echo
echo "Watch health:"
curl -fsS "http://127.0.0.1:${AXON_WATCH_WATCH_SERVICE_PORT}/internal/watch/health"
echo
echo "Watch readiness:"
curl -fsS "http://127.0.0.1:${AXON_WATCH_WATCH_SERVICE_PORT}/internal/watch/readiness"
echo
