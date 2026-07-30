#!/usr/bin/env bash
# Update Cloudflare named-tunnel ingress to Axon-X :4173 via API.
# Requires Tunnel:Edit API token from (first match wins):
#   1) CF_API_TOKEN / CLOUDFLARE_API_TOKEN env
#   2) ~/.config/axon-watch/deployment.env
#   3) Unlocked vault secret CF_API_TOKEN or CLOUDFLARE_API_TOKEN
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
env_file="${AXON_WATCH_DEPLOYMENT_ENV:-${HOME}/.config/axon-watch/deployment.env}"
cp_url="${AXON_WATCH_CONTROL_PLANE_BASE_URL:-http://127.0.0.1:8787}"

# Default account id decoded from the named-tunnel token payload (not a secret).
: "${CF_ACCOUNT_ID:=1617b61e378ca70f402d82133c3a06b1}"
TUNNEL_ID="${CF_TUNNEL_ID:-c2995e01-b0bc-41a7-93cf-dc6e515a86ca}"
ORIGIN="${AXON_TUNNEL_ORIGIN:-http://127.0.0.1:4173}"
HOSTNAME="${AXON_TUNNEL_HOSTNAME:-axon.edudashpro.org.za}"

read_env_key() {
  local key="$1"
  if [[ -n "${!key:-}" ]]; then
    printf '%s' "${!key}"
    return 0
  fi
  if [[ -f "${env_file}" ]]; then
    local line
    line="$(rg -N "^${key}=" "${env_file}" | head -n1 || true)"
    if [[ -n "${line}" ]]; then
      printf '%s' "${line#*=}"
      return 0
    fi
  fi
  return 1
}

read_operator_token() {
  read_env_key AXON_WATCH_OPERATOR_TOKEN || true
}

read_vault_secret_password() {
  local want_name="$1"
  local op_token
  op_token="$(read_operator_token)"
  if [[ -z "${op_token}" ]]; then
    return 1
  fi
  AXON_CP_URL="${cp_url}" AXON_OP_TOKEN="${op_token}" AXON_SECRET_NAME="${want_name}" python3 - <<'PY'
import json, os, urllib.request
cp = os.environ["AXON_CP_URL"].rstrip("/")
token = os.environ["AXON_OP_TOKEN"]
want = os.environ["AXON_SECRET_NAME"]
headers = {"Accept": "application/json", "Authorization": f"Bearer {token}"}
req = urllib.request.Request(f"{cp}/api/vault/secrets", headers=headers)
try:
    with urllib.request.urlopen(req, timeout=20) as response:
        items = json.loads(response.read().decode())
except Exception:
    raise SystemExit(1)
sid = None
for item in items if isinstance(items, list) else []:
    if str(item.get("name") or "").strip() == want:
        sid = item.get("id")
        break
if not sid:
    raise SystemExit(1)
req = urllib.request.Request(f"{cp}/api/vault/secrets/{sid}", headers=headers)
with urllib.request.urlopen(req, timeout=20) as response:
    detail = json.loads(response.read().decode())
password = str(detail.get("password") or "").strip()
if not password:
    raise SystemExit(1)
print(password, end="")
PY
}

resolve_cf_api_token() {
  local token=""
  token="$(read_env_key CF_API_TOKEN 2>/dev/null || true)"
  if [[ -z "${token}" ]]; then
    token="$(read_env_key CLOUDFLARE_API_TOKEN 2>/dev/null || true)"
  fi
  if [[ -z "${token}" ]]; then
    token="$(read_vault_secret_password CF_API_TOKEN 2>/dev/null || true)"
  fi
  if [[ -z "${token}" ]]; then
    token="$(read_vault_secret_password CLOUDFLARE_API_TOKEN 2>/dev/null || true)"
  fi
  printf '%s' "${token}"
}

CF_API_TOKEN="$(resolve_cf_api_token)"
if [[ -z "${CF_API_TOKEN}" ]]; then
  cat <<EOF >&2
ERROR: CF_API_TOKEN not found.

Create a Cloudflare API token with Account → Cloudflare Tunnel → Edit, then either:

  echo 'CF_API_TOKEN=...' >> ${env_file}
  # or store vault secret named CF_API_TOKEN while vault is unlocked

Then re-run:
  ./scripts/ops/set-tunnel-ingress-4173.sh
EOF
  exit 2
fi

payload="$(python3 - <<PY
import json
print(json.dumps({
  "config": {
    "ingress": [
      {"hostname": "${HOSTNAME}", "service": "${ORIGIN}"},
      {"service": "http_status:404"},
    ]
  }
}))
PY
)"

url="https://api.cloudflare.com/client/v4/accounts/${CF_ACCOUNT_ID}/cfd_tunnel/${TUNNEL_ID}/configurations"
echo "PUT ${url}"
echo "  hostname=${HOSTNAME}  service=${ORIGIN}"
curl -sS -X PUT "${url}" \
  -H "Authorization: Bearer ${CF_API_TOKEN}" \
  -H "Content-Type: application/json" \
  --data "${payload}" | python3 -m json.tool

echo
echo "Verify:"
echo "  curl -sS ${ORIGIN}/api/health"
echo "  curl -sS https://${HOSTNAME}/api/health"
echo "  # Mission Control → Connectors → REPROBE Cloudflare tunnel"
echo "  # Expect ingress_matches_axon=true (no soft cutover / no :7734 legacy chip)"
