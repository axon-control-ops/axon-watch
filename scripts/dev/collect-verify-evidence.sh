#!/usr/bin/env bash
# Measure warm-route latency samples and shell boot readiness for verify gates.
# Requires the dev stack to be running (./scripts/dev/up.sh).

set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
source "${repo_root}/scripts/dev/lib/common.sh"

load_env

if [[ -x "${repo_root}/.venv/bin/python3" ]]; then
  PYTHON="${repo_root}/.venv/bin/python3"
else
  PYTHON="python3"
fi

output_dir="${1:-${repo_root}/.local/verify}"
request_count="${AXON_WATCH_LATENCY_SAMPLES:-15}"
mkdir -p "${output_dir}"

measure_url() {
  local url="$1"
  local count="$2"
  "${PYTHON}" - "${url}" "${count}" <<'PY'
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
watch_url="$(service_base_url axon-watch)/internal/watch/summary"
live_url="$(service_base_url control-plane)/api/live/events"

echo "Collecting ${request_count} runtime summary samples from ${runtime_url}"
measure_url "${runtime_url}" "${request_count}" >"${output_dir}/runtime-summary-latency.json"

echo "Collecting ${request_count} watch summary samples from ${watch_url}"
measure_url "${watch_url}" "${request_count}" >"${output_dir}/watch-summary-latency.json"

echo "Measuring shell boot readiness from ${AXON_WATCH_PUBLIC_BASE_URL}"
"${PYTHON}" "${repo_root}/scripts/dev/measure_shell_boot.py" \
  --console-base-url "${AXON_WATCH_PUBLIC_BASE_URL}" \
  --control-plane-base-url "${AXON_WATCH_CONTROL_PLANE_BASE_URL}" \
  --mode "${AXON_WATCH_SHELL_BOOT_MODE:-auto}" \
  --output "${output_dir}/shell-boot-report.json"

echo "Wrote verify evidence to ${output_dir}/"
ls -1 "${output_dir}"

echo "Probing live events endpoint (connected frame)..."
live_events_chunk="$(
  curl -sS --max-time 2 -H 'Accept: text/event-stream' "${live_url}" 2>/dev/null | head -c 256
)" || true
if [[ "${live_events_chunk}" == *connected* ]]; then
  printf '%s\n' "${live_events_chunk%%$'\n'*}"
  echo "ok ${live_url}"
else
  echo "warn: live events probe failed (stack may be starting)" >&2
fi
