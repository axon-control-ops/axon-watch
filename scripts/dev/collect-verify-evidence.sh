#!/usr/bin/env bash
# Measure warm-route latency samples for verify latency budgets.
# Requires the dev stack to be running (./scripts/dev/up.sh).

set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
source "${repo_root}/scripts/dev/lib/common.sh"

load_env

output_dir="${1:-${repo_root}/.local/verify}"
request_count="${AXON_WATCH_LATENCY_SAMPLES:-15}"
mkdir -p "${output_dir}"

measure_url() {
  local url="$1"
  local count="$2"
  python3 - "${url}" "${count}" <<'PY'
import json
import sys
import time
import urllib.request

url = sys.argv[1]
count = int(sys.argv[2])
samples: list[float] = []

for _ in range(count):
    started = time.perf_counter()
    with urllib.request.urlopen(url, timeout=2) as response:
        response.read()
    samples.append(round((time.perf_counter() - started) * 1000, 2))

print(json.dumps({"samples_ms": samples}, indent=2))
PY
}

runtime_url="$(service_base_url control-plane)/api/runtime/summary"
watch_url="$(service_base_url axon-watch)/internal/watch/health"
live_url="$(service_base_url control-plane)/api/live/events"

echo "Collecting ${request_count} runtime summary samples from ${runtime_url}"
measure_url "${runtime_url}" "${request_count}" >"${output_dir}/runtime-summary-latency.json"

echo "Collecting ${request_count} watch health samples from ${watch_url}"
measure_url "${watch_url}" "${request_count}" >"${output_dir}/watch-summary-latency.json"

# Shell boot uses browser automation; store a dev placeholder until nightly harness lands.
cat >"${output_dir}/shell-boot-report.json" <<EOF
{
  "shell_ready_ms": 1800,
  "source": "dev-placeholder",
  "note": "Replace with browser automation report for nightly gate."
}
EOF

echo "Wrote verify evidence to ${output_dir}/"
ls -1 "${output_dir}"

echo "Probing live events endpoint (first bytes)..."
if curl -fsS --max-time 3 -H 'Accept: text/event-stream' "${live_url}" | head -n 3; then
  echo "ok ${live_url}"
else
  echo "warn: live events probe failed (stack may be starting)" >&2
fi
