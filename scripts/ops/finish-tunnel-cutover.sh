#!/usr/bin/env bash
# Finish exclusive Axon-X tunnel ownership and verify public origin.
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${repo_root}"

PUBLIC_URL="${AXON_PUBLIC_URL:-https://axon.edudashpro.org.za}"
CP_URL="${AXON_WATCH_CONTROL_PLANE_BASE_URL:-http://127.0.0.1:8787}"
TARGET_ORIGIN="${AXON_TUNNEL_ORIGIN:-http://127.0.0.1:4173}"

echo "==> Disable root systemd cloudflared (requires privilege)"
if systemctl is-active --quiet cloudflared 2>/dev/null || systemctl is-enabled --quiet cloudflared 2>/dev/null; then
  if command -v pkexec >/dev/null 2>&1; then
    pkexec systemctl disable --now cloudflared
  else
    sudo systemctl disable --now cloudflared
  fi
else
  echo "cloudflared.service already inactive/disabled"
fi

echo "==> Ensure Axon-X managed tunnel is running"
curl -sS -X POST "${CP_URL}/api/tunnel/start" | python3 -m json.tool

sleep 2
echo "==> Tunnel status"
curl -sS "${CP_URL}/api/tunnel/status" | python3 -m json.tool

echo "==> Process check (expect a single non-root or Axon-managed cloudflared)"
ps -eo pid,user,cmd | rg 'cloudflared' | rg -v 'rg |finish-tunnel' || true

echo
echo "==> Cloudflare remote ingress must target ${TARGET_ORIGIN}"
echo "    Dashboard: Zero Trust → Networks → Tunnels → axon → Public Hostname"
echo "    Hostname: axon.edudashpro.org.za"
echo "    Service:  ${TARGET_ORIGIN}"
echo
echo "Optional API cutover when CF_API_TOKEN + CF_ACCOUNT_ID are set:"
echo "  CF_API_TOKEN=... CF_ACCOUNT_ID=... ./scripts/ops/set-tunnel-ingress-4173.sh"

echo "==> Public health probe"
code="$(curl -sS -o /tmp/axon-public-health.json -w '%{http_code}' --max-time 10 "${PUBLIC_URL}/api/health" || true)"
echo "HTTP ${code}"
head -c 200 /tmp/axon-public-health.json 2>/dev/null || true
echo
