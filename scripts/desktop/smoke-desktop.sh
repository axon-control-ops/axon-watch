#!/usr/bin/env bash
# Smoke-check packaged desktop prerequisites on this host.
# Full clean-VM install is documented in the handbook; this script verifies
# local artifacts + Azure TTS + API session bootstrap without mutating packages.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

DEB="apps/console-desktop/src-tauri/target/release/bundle/deb/VAXON_0.1.0_amd64.deb"
test -f "$DEB"
echo "deb_ok=$(du -h "$DEB" | awk '{print $1}')"

# Auth via vite proxy (always-on path)
curl -fsS -H 'Content-Type: application/json' \
  -d '{"text":"VAXON desktop voice smoke."}' \
  http://127.0.0.1:4173/api/kairo/tts \
  | python3 -c 'import json,sys; p=json.load(sys.stdin); assert p.get("available") and p.get("provider")=="azure" and p.get("audio_base64"); print("azure_tts_ok", p.get("voice"), "bytes", len(p.get("audio_base64") or ""))'

curl -fsS http://127.0.0.1:4173/api/kairo/stt \
  | python3 -c 'import json,sys; p=json.load(sys.stdin); assert p.get("available"); print("azure_stt_ok", p.get("provider"))'

# Desktop bootstrap against live CP (uses deployment token when present)
TOKEN=""
if [[ -f "$HOME/.config/axon-watch/deployment.env" ]]; then
  TOKEN="$(rg -n '^AXON_WATCH_OPERATOR_TOKEN=' "$HOME/.config/axon-watch/deployment.env" | head -n1 | cut -d= -f2- | tr -d \"\' )"
fi
if [[ -n "$TOKEN" && "$TOKEN" != "replace-me" ]]; then
  curl -fsS -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
    -d "{\"operator_token\":\"$TOKEN\"}" \
    http://127.0.0.1:8787/api/desktop/bootstrap \
    | python3 -c 'import json,sys; p=json.load(sys.stdin); assert p.get("ok"); print("desktop_bootstrap_ok")'
else
  echo "desktop_bootstrap_skipped (no operator token)"
fi

echo "desktop_smoke_ok"
