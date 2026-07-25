#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

export PYTHONPATH="$ROOT/services/control-plane"
export AXON_WATCH_RESEARCH_ENABLED=1

python3 - <<'PY'
from app.research.service import fetch_url, search_web

search = search_web("Axon-X operator console")
assert search.get("success") is True, search
assert int(search.get("count") or 0) >= 0

fetch = fetch_url("https://example.com/")
assert fetch.get("success") is True, fetch
assert "Example Domain" in str(fetch.get("content") or "")

print("research-smoke: ok")
PY
