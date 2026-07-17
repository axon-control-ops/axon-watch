#!/usr/bin/env bash
# Start a local SearXNG instance for Axon-X research (meta-search / whole web).
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
source "${repo_root}/scripts/dev/lib/common.sh"

load_env

name="${AXON_WATCH_SEARXNG_CONTAINER:-axon-watch-searxng}"
port="${AXON_WATCH_SEARXNG_PORT:-8080}"
base_url="http://127.0.0.1:${port}"
settings_file="${repo_root}/config/searxng/settings.yml"

if ! command -v docker >/dev/null 2>&1; then
  echo "docker is required to run SearXNG locally." >&2
  exit 1
fi

if docker ps -a --format '{{.Names}}' | grep -qx "${name}"; then
  echo "Removing prior container ${name} to apply settings..."
  docker rm -f "${name}" >/dev/null
fi

echo "Creating SearXNG container ${name} on ${base_url} ..."
docker run -d \
  --name "${name}" \
  --restart unless-stopped \
  -p "127.0.0.1:${port}:8080" \
  -e "SEARXNG_BASE_URL=${base_url}/" \
  -e "SEARXNG_LIMITER=false" \
  -v "${settings_file}:/etc/searxng/settings.yml:ro" \
  searxng/searxng:latest >/dev/null

deadline=$((SECONDS + 45))
until curl -fsS "${base_url}/search?q=ping&format=json" >/dev/null 2>&1; do
  if (( SECONDS >= deadline )); then
    echo "SearXNG did not become ready on ${base_url}" >&2
    docker logs --tail 40 "${name}" >&2 || true
    exit 1
  fi
  sleep 1
done

echo "SearXNG ready: ${base_url}"
echo "Set in .env or vault: AXON_WATCH_SEARXNG_URL=${base_url}"
