#!/usr/bin/env bash
# Update Cloudflare named-tunnel ingress to Axon-X :4173 via API.
# Requires: CF_API_TOKEN (Tunnel:Edit), CF_ACCOUNT_ID, optional CF_TUNNEL_ID.
set -euo pipefail

: "${CF_API_TOKEN:?Set CF_API_TOKEN with Cloudflare Tunnel Edit permission}"
# Default account id decoded from the named-tunnel token payload (not a secret).
: "${CF_ACCOUNT_ID:=1617b61e378ca70f402d82133c3a06b1}"
TUNNEL_ID="${CF_TUNNEL_ID:-c2995e01-b0bc-41a7-93cf-dc6e515a86ca}"
ORIGIN="${AXON_TUNNEL_ORIGIN:-http://127.0.0.1:4173}"
HOSTNAME="${AXON_TUNNEL_HOSTNAME:-axon.edudashpro.org.za}"

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
curl -sS -X PUT "${url}" \
  -H "Authorization: Bearer ${CF_API_TOKEN}" \
  -H "Content-Type: application/json" \
  --data "${payload}" | python3 -m json.tool

echo "Verify remote config was accepted, then:"
echo "  curl -sS ${ORIGIN%/4173}/api/health  # local"
echo "  curl -sS https://${HOSTNAME}/api/health"
