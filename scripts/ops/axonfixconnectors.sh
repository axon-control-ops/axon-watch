#!/usr/bin/env bash
# One-word: axonfixconnectors
# Diagnose and remediate Mission Control "REQUIRED CONNECTOR DOWN" /
# "tunnel token missing" / vault unlock HTTP 503 on a public-URL host.
#
# Typical failure chain on this always-on host:
#   public AXON_WATCH_PUBLIC_BASE_URL
#     → remotely reachable
#     → missing AXON_WATCH_INTERNAL_SERVICE_TOKEN
#     → vault unlock / tunnel start via CP→watch fail (HTTP 503)
#     → vault stays locked → tunnel token unavailable
#     → console_web probes https://…/api/health → required connector down
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cp_url="${AXON_WATCH_CONTROL_PLANE_BASE_URL:-http://127.0.0.1:8787}"
env_file="${AXON_WATCH_DEPLOYMENT_ENV:-${HOME}/.config/axon-watch/deployment.env}"
ensure_token=0
start_tunnel=1
reprobe=1
restart_after_token=0

# Remotely reachable hosts force AXON_WATCH_AUTH_MODE=local_token. Mutating
# control-plane routes need the operator bearer (or a desktop session cookie).
# Read from deployment.env without printing the value.
operator_token="${AXON_WATCH_OPERATOR_TOKEN:-}"
if [[ -z "${operator_token}" && -f "${env_file}" ]]; then
  operator_token="$(rg -N '^AXON_WATCH_OPERATOR_TOKEN=' "${env_file}" | head -n1 | cut -d= -f2- || true)"
fi

usage() {
  cat <<'EOF'
Usage: axonfixconnectors [--ensure-internal-token] [--restart] [--no-tunnel] [--no-reprobe]

  Diagnose connector / tunnel / vault blockers. Optionally mint the shared
  internal service token required when the public URL is non-loopback.

Options:
  --ensure-internal-token  If AXON_WATCH_INTERNAL_SERVICE_TOKEN is missing,
                           append a fresh openssl rand -hex 24 to deployment.env
  --restart                After ensuring the token, run axonrestart
  --no-tunnel              Skip POST /api/tunnel/start
  --no-reprobe             Skip reprobe_connector for console_web + cloudflare_tunnel
  -h, --help               Show this help
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --ensure-internal-token) ensure_token=1 ;;
    --restart) restart_after_token=1 ;;
    --no-tunnel) start_tunnel=0 ;;
    --no-reprobe) reprobe=0 ;;
    -h|--help) usage; exit 0 ;;
    *)
      echo "Unknown option: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
  shift
done

json_get() {
  # Usage: json_get <json> <python-expr-on-obj-as-d>
  local payload="$1"
  local expr="$2"
  AXON_JSON_PAYLOAD="${payload}" python3 -c "
import json, os
d = json.loads(os.environ['AXON_JSON_PAYLOAD'])
print(${expr})
"
}

curl_json() {
  local method="$1"
  local url="$2"
  local data="${3:-}"
  local -a headers=(-H 'Accept: application/json')
  if [[ -n "${operator_token}" ]]; then
    headers+=(-H "Authorization: Bearer ${operator_token}")
  fi
  if [[ -n "${data}" ]]; then
    curl -sS --max-time 25 -X "${method}" \
      "${headers[@]}" \
      -H 'Content-Type: application/json' \
      -d "${data}" \
      "${url}"
  else
    curl -sS --max-time 25 -X "${method}" \
      "${headers[@]}" \
      "${url}"
  fi
}

env_has_key() {
  local key="$1"
  [[ -f "${env_file}" ]] || return 1
  rg -q "^${key}=" "${env_file}"
}

env_key_set() {
  local key="$1"
  [[ -f "${env_file}" ]] || return 1
  # Non-empty value after =
  rg -q "^${key}=.+" "${env_file}"
}

echo "Axon-X connector / tunnel fix"
echo "  control-plane: ${cp_url}"
echo "  deployment.env: ${env_file}"
echo

# --- Diagnose deployment identity ---
public_url=""
if [[ -f "${env_file}" ]]; then
  public_url="$(rg -N '^AXON_WATCH_PUBLIC_BASE_URL=' "${env_file}" | head -n1 | cut -d= -f2- || true)"
fi
public_url="${public_url:-${AXON_WATCH_PUBLIC_BASE_URL:-}}"
echo "==> Public base URL: ${public_url:-'(unset)'}"

remote=0
if [[ -n "${public_url}" ]] && ! [[ "${public_url}" =~ ^https?://(127\.0\.0\.1|localhost|\[::1\])(:|/|$) ]]; then
  remote=1
  echo "    Remotely reachable: yes (auto-unlock refused; internal token required)"
else
  echo "    Remotely reachable: no (loopback / unset)"
fi

token_present=0
if env_key_set "AXON_WATCH_INTERNAL_SERVICE_TOKEN" || [[ -n "${AXON_WATCH_INTERNAL_SERVICE_TOKEN:-}" ]]; then
  token_present=1
  echo "    AXON_WATCH_INTERNAL_SERVICE_TOKEN: present"
else
  echo "    AXON_WATCH_INTERNAL_SERVICE_TOKEN: MISSING"
fi

if [[ "${remote}" -eq 1 && "${token_present}" -eq 0 ]]; then
  echo
  echo "BLOCKER: vault unlock / tunnel start will fail with:"
  echo "  Watch vault API HTTP 503: AXON_WATCH_INTERNAL_SERVICE_TOKEN is required"
  echo "  when the operator surface is remotely reachable"
  if [[ "${ensure_token}" -eq 1 ]]; then
    mkdir -p "$(dirname "${env_file}")"
    touch "${env_file}"
    chmod 600 "${env_file}"
    minted="$(openssl rand -hex 24)"
    if env_has_key "AXON_WATCH_INTERNAL_SERVICE_TOKEN"; then
      # Replace empty / ensure non-empty without printing value
      tmp="$(mktemp)"
      awk -v v="${minted}" '
        BEGIN { done=0 }
        /^AXON_WATCH_INTERNAL_SERVICE_TOKEN=/ {
          print "AXON_WATCH_INTERNAL_SERVICE_TOKEN=" v
          done=1
          next
        }
        { print }
        END { if (!done) print "AXON_WATCH_INTERNAL_SERVICE_TOKEN=" v }
      ' "${env_file}" >"${tmp}"
      mv "${tmp}" "${env_file}"
      chmod 600 "${env_file}"
    else
      printf '\nAXON_WATCH_INTERNAL_SERVICE_TOKEN=%s\n' "${minted}" >>"${env_file}"
    fi
    unset minted
    token_present=1
    echo "    Minted AXON_WATCH_INTERNAL_SERVICE_TOKEN into ${env_file}"
    if [[ "${restart_after_token}" -eq 1 ]]; then
      echo
      echo "==> Restarting stack so both services load the token..."
      "${repo_root}/scripts/ops/axonrestart.sh"
    else
      echo
      echo "NEXT: run  axonrestart  (or  axonfixconnectors --ensure-internal-token --restart)"
      echo "      then unlock Vault in the console (Remember me), then re-run axonfixconnectors."
      exit 2
    fi
  else
    echo
    echo "Fix:"
    echo "  axonfixconnectors --ensure-internal-token --restart"
    echo "  # or manually:"
    echo "  echo \"AXON_WATCH_INTERNAL_SERVICE_TOKEN=\$(openssl rand -hex 24)\" >> ${env_file}"
    echo "  axonrestart"
    echo "  # then unlock Vault at /vault (Remember me), then re-run this command"
    exit 2
  fi
fi

# --- Live probes ---
echo
echo "==> Tunnel status"
tunnel_json="$(curl_json GET "${cp_url}/api/tunnel/status" || true)"
if [[ -z "${tunnel_json}" ]]; then
  echo "    FAILED to reach ${cp_url}/api/tunnel/status"
  exit 1
fi
tunnel_status="$(json_get "${tunnel_json}" "d.get('status','')")"
tunnel_detail="$(json_get "${tunnel_json}" "d.get('detail','')")"
tunnel_auth="$(json_get "${tunnel_json}" "d.get('auth_source','')")"
tunnel_running="$(json_get "${tunnel_json}" "d.get('running', False)")"
echo "    status=${tunnel_status}  auth_source=${tunnel_auth}  running=${tunnel_running}"
echo "    detail=${tunnel_detail}"

echo
echo "==> Connectors summary"
connectors_json="$(curl_json GET "${cp_url}/api/connectors" || true)"
if [[ -z "${connectors_json}" ]]; then
  echo "    FAILED to reach ${cp_url}/api/connectors"
  exit 1
fi
python3 - "${connectors_json}" <<'PY'
import json, sys
payload = json.loads(sys.argv[1])
summary = payload.get("summary") or {}
print(
    "    configured={configured} ok={ok} degraded={degraded} "
    "unavailable={unavailable} required_unavailable={required_unavailable}".format(
        configured=summary.get("configured", 0),
        ok=summary.get("ok", 0),
        degraded=summary.get("degraded", 0),
        unavailable=summary.get("unavailable", 0),
        required_unavailable=summary.get("required_unavailable", 0),
    )
)
for item in payload.get("items") or []:
    if not isinstance(item, dict):
        continue
    cid = item.get("connector_id") or ""
    if cid in {"console_web", "cloudflare_tunnel", "control_plane"} or item.get("required"):
        print(
            f"    - {cid}: {item.get('status')} — {item.get('detail') or ''}".rstrip(" —")
        )
PY

if [[ "${tunnel_auth}" == "missing" ]]; then
  echo
  echo "BLOCKER: tunnel token missing (auth=missing)."
  echo "  1. Open http://127.0.0.1:4173/vault (or :5173/vault)"
  echo "  2. Unlock with master password + 2FA (check Remember me)"
  echo "  3. Confirm vault secret exists: cloudflare_tunnel_token"
  echo "     (or AXON_CLOUDFLARE_TUNNEL_TOKEN / CLOUDFLARE_TUNNEL_TOKEN / TUNNEL_TOKEN)"
  echo "  4. Re-run: axonfixconnectors"
  echo "  Alternate (persistent, no vault): put AXON_CLOUDFLARE_TUNNEL_TOKEN=... in"
  echo "     ${env_file} then axonrestart"
  exit 2
fi

if [[ "${start_tunnel}" -eq 1 || "${reprobe}" -eq 1 ]]; then
  if [[ -z "${operator_token}" ]]; then
    echo
    echo "BLOCKER: mutating API needs Authorization: Bearer <operator token>."
    echo "  Set AXON_WATCH_OPERATOR_TOKEN in ${env_file} (already required for local_token),"
    echo "  or Start tunnel / REPROBE from Mission Control (desktop session cookie)."
    exit 2
  fi
  echo "    Operator bearer: present (used for tunnel start / reprobe)"
fi

if [[ "${start_tunnel}" -eq 1 && "${tunnel_running}" != "True" ]]; then
  echo
  echo "==> Starting managed tunnel"
  start_json="$(curl_json POST "${cp_url}/api/tunnel/start" || true)"
  if [[ -z "${start_json}" ]]; then
    echo "    FAILED POST /api/tunnel/start"
    exit 1
  fi
  start_detail="$(json_get "${start_json}" "d.get('msg') or d.get('detail') or d.get('status') or ''")"
  echo "    ${start_detail}"
  if [[ "${start_detail}" == *"Authorization: Bearer"* || "${start_detail}" == *"auth_required"* ]]; then
    echo "    Tunnel start rejected — operator token missing/wrong for local_token mode."
    exit 2
  fi
  sleep 2
fi

if [[ "${reprobe}" -eq 1 ]]; then
  echo
  echo "==> Reprobe console_web + cloudflare_tunnel + refresh summary"
  for target in console_web cloudflare_tunnel; do
    curl_json POST "${cp_url}/api/watch/commands" \
      "{\"command_type\":\"reprobe_connector\",\"target_type\":\"connector\",\"target_id\":\"${target}\",\"requested_by\":\"axonfixconnectors\"}" \
      >/dev/null || true
  done
  curl_json POST "${cp_url}/api/watch/commands" \
    '{"command_type":"refresh_summary","requested_by":"axonfixconnectors"}' \
    >/dev/null || true
  sleep 1
fi

echo
echo "==> Final connectors summary"
final_json="$(curl_json GET "${cp_url}/api/connectors" || true)"
python3 - "${final_json}" <<'PY'
import json, sys
payload = json.loads(sys.argv[1] or "{}")
summary = payload.get("summary") or {}
req = int(summary.get("required_unavailable") or 0)
print(
    "    required_unavailable={req}  ok={ok}/{configured}".format(
        req=req,
        ok=summary.get("ok", 0),
        configured=summary.get("configured", 0),
    )
)
for item in payload.get("items") or []:
    if not isinstance(item, dict):
        continue
    if item.get("connector_id") in {"console_web", "cloudflare_tunnel"}:
        print(
            f"    - {item.get('connector_id')}: {item.get('status')} — {item.get('detail') or ''}".rstrip(" —")
        )
raise SystemExit(1 if req > 0 else 0)
PY

echo
echo "Done. Hard-refresh Mission Control if the rail still looks stale."
echo "Console: http://127.0.0.1:4173"
