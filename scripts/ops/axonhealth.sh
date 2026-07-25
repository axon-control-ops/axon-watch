#!/usr/bin/env bash
# One-word: axonhealth
# Probe console + control-plane + watch (+ key APIs).
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
exec "${repo_root}/scripts/dev/check-health.sh"
