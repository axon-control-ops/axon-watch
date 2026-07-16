#!/usr/bin/env bash
# Robust verification for the operator "needs attention" cutover list.
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${repo_root}"

CP="${AXON_WATCH_CONTROL_PLANE_BASE_URL:-http://127.0.0.1:8787}"
WATCH="${AXON_WATCH_WATCH_SERVICE_BASE_URL:-http://127.0.0.1:8788}"
PUBLIC="${AXON_PUBLIC_URL:-https://axon.edudashpro.org.za}"
LEGACY="${AXON_LEGACY_URL:-http://127.0.0.1:7735}"
fail=0
tmp="$(mktemp -d)"
trap 'rm -rf "${tmp}"' EXIT

pass() { echo "PASS  $*"; }
fail_item() { echo "FAIL  $*"; fail=1; }
info() { echo "INFO  $*"; }
warn_item() { echo "WARN  $*"; }

echo "=== Attention-blocker verification ==="

if systemctl is-active --quiet cloudflared 2>/dev/null; then
  fail_item "cloudflared.service still active"
else
  pass "cloudflared.service inactive"
fi
if systemctl is-enabled --quiet cloudflared 2>/dev/null; then
  fail_item "cloudflared.service still enabled"
else
  pass "cloudflared.service disabled"
fi

cf_count="$(pgrep -x cloudflared | wc -l | tr -d ' ')"
if [[ "${cf_count}" == "1" ]]; then
  pass "exactly one cloudflared process"
elif [[ "${cf_count}" == "0" ]]; then
  fail_item "no cloudflared process running"
else
  fail_item "expected 1 cloudflared process, found ${cf_count}"
fi

curl -sS --max-time 8 "${CP}/api/tunnel/status" -o "${tmp}/tunnel.json" || true
if python3 - <<PY
import json
from pathlib import Path
path = Path("${tmp}/tunnel.json")
if not path.is_file() or not path.read_text().strip():
    print("FAIL  tunnel status missing")
    raise SystemExit(1)
d = json.loads(path.read_text())
detail = str(d.get("detail") or "")
status = str(d.get("status") or "")
if not d.get("managed"):
    print("FAIL  tunnel managed!=true detail=%s" % detail)
    raise SystemExit(1)
if "multiple cloudflared" in detail:
    print("FAIL  tunnel detail still reports multiple processes:", detail)
    raise SystemExit(1)
if status != "ok":
    print("FAIL  tunnel status=%s detail=%s" % (status, detail))
    raise SystemExit(1)
print("PASS  tunnel managed=true pid=%s status=ok" % d.get("pid"))
PY
then
  :
else
  fail=1
fi

ingress="$(python3 - <<'PY'
from pathlib import Path
import re
text = Path(".local/state/tunnel/cloudflared.log").read_text(errors="replace").replace('\\"', '"')
matches = re.findall(r'"hostname"\s*:\s*"([^"]+)"\s*,\s*"service"\s*:\s*"([^"]+)"', text)
print(matches[-1][1] if matches else "")
PY
)"
info "remote ingress service=${ingress:-unknown}"

pub_code="$(curl -sS -o "${tmp}/public-health.json" -w '%{http_code}' --max-time 15 "${PUBLIC}/api/health" || true)"
if [[ "${pub_code}" == "200" ]] && rg -q '"service"\s*:\s*"control-plane"' "${tmp}/public-health.json"; then
  pass "public /api/health serves Axon-X control-plane"
  if [[ "${ingress}" == "http://127.0.0.1:4173" || "${ingress}" == "http://localhost:4173" ]]; then
    pass "remote ingress targets Axon-X :4173"
  elif [[ "${ingress}" == "http://localhost:7734" || "${ingress}" == "http://127.0.0.1:7734" ]]; then
    pass "soft cutover active (CF :7734 origin proxies Axon-X)"
  else
    warn_item "unexpected remote ingress '${ingress}' but public Axon-X OK"
  fi
else
  fail_item "public /api/health not Axon-X (HTTP ${pub_code}); body=$(head -c 120 "${tmp}/public-health.json" 2>/dev/null | tr '\n' ' ')"
fi

if curl -sS --max-time 5 "${LEGACY}/api/health" -o "${tmp}/legacy-health.json"; then
  if rg -qi 'axon-local|"port"\s*:\s*7735' "${tmp}/legacy-health.json"; then
    pass "legacy axon-local soft-rollback on :7735"
  else
    warn_item "legacy :7735 responded but body unexpected"
  fi
else
  warn_item "legacy soft-rollback :7735 not reachable (WhatsApp local path)"
fi

watch_count="$(curl -sS --max-time 20 "${WATCH}/internal/watch/inbox" | python3 -c 'import sys,json; print(json.load(sys.stdin).get("count",0))')"
cp_code="$(curl -sS -o "${tmp}/cp-inbox.json" -w '%{http_code}' --max-time 20 "${CP}/api/inbox" || true)"
cp_count="$(python3 -c 'import json; from pathlib import Path; print(json.loads(Path("'"${tmp}"'/cp-inbox.json").read_text()).get("count",-1))' 2>/dev/null || echo -1)"
info "watch_inbox=${watch_count} cp_inbox_http=${cp_code} cp_count=${cp_count}"
if [[ "${cp_code}" == "503" ]]; then
  fail_item "control-plane inbox unavailable (503)"
elif [[ "${cp_code}" == "200" && "${watch_count}" -gt 0 && "${cp_count}" -eq 0 ]]; then
  fail_item "false-empty CP inbox (watch=${watch_count}, cp=0)"
elif [[ "${cp_code}" == "200" ]]; then
  pass "control-plane inbox healthy (count=${cp_count})"
else
  fail_item "unexpected CP inbox HTTP ${cp_code}"
fi

if python3 - <<PY
import json, urllib.request
watch = json.load(urllib.request.urlopen("${WATCH}/internal/watch/inbox", timeout=20))
bad = []
for item in watch.get("items") or []:
    if item.get("source") != "email":
        continue
    meta = item.get("meta") or {}
    acct = str(meta.get("email_account_address") or "")
    ws = str(item.get("workspace_id") or "")
    if acct == "superadmin@edudashpro.org.za" and ws != "workspace_dashpro":
        bad.append((item.get("signal_id"), ws))
    if acct == "axonops@edudashpro.org.za" and ws != "workspace_axon_watch":
        bad.append((item.get("signal_id"), ws))
if bad:
    print("FAIL  misrouted mailbox workspaces:", bad)
    raise SystemExit(1)
print("PASS  email signals follow mailbox workspace ownership")
PY
then
  :
else
  fail=1
fi

if python3 - <<PY
import json, urllib.request
settings = json.load(urllib.request.urlopen("${CP}/api/email/settings", timeout=20))
auth = settings.get("auth") or {}
assert auth.get("configured") and not auth.get("locked"), auth
accounts = {(a.get("email_address"), a.get("workspace_id")) for a in settings["settings"]["accounts"]}
need = {
    ("axonops@edudashpro.org.za", "workspace_axon_watch"),
    ("superadmin@edudashpro.org.za", "workspace_dashpro"),
}
missing = need - accounts
if missing:
    print("FAIL  missing mailbox/workspace bindings", missing)
    raise SystemExit(1)
for a in settings["settings"]["accounts"]:
    if not a.get("imap", {}).get("password_ref") or not a.get("smtp", {}).get("password_ref"):
        print("FAIL  missing vault password_ref for", a.get("email_address"))
        raise SystemExit(1)
print("PASS  both mailboxes configured with vault password refs")
PY
then
  :
else
  fail=1
fi

if ./scripts/dev/check-health.sh >"${tmp}/check-health.out" 2>&1; then
  pass "scripts/dev/check-health.sh"
else
  fail_item "scripts/dev/check-health.sh"
  tail -n 20 "${tmp}/check-health.out" || true
fi

python3 -B -m unittest \
  tests.test_control_plane_inbox_projection \
  tests.test_email_account_resolve \
  tests.test_email_smtp_send \
  tests.test_scanned_workbook_gate \
  -q
PYTHONPATH=services/axon-watch python3 -B -m unittest \
  tests.test_email_signal \
  tests.test_tunnel_remote_control \
  -q
pass "unit suites (inbox/email/tunnel/vision)"

echo
if [[ "${fail}" -eq 0 ]]; then
  echo "ALL ATTENTION BLOCKERS VERIFIED"
  exit 0
fi
echo "SOME ATTENTION BLOCKERS REMAIN"
exit 1
