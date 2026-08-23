#!/usr/bin/env bash
# Install the pinned, checksum-verified cloudflared onto the system disk.
#
# Deliberately operator-driven: watch startup must never download a binary.
# The pin (version + per-arch sha256) lives in config/cloudflared-pin.json.
#
# Usage:
#   ./scripts/ops/install-cloudflared.sh            # install if missing/changed
#   ./scripts/ops/install-cloudflared.sh --force    # re-download and reverify
#   ./scripts/ops/install-cloudflared.sh --status   # report without network use
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
mode="install"
case "${1:-}" in
  --force) mode="force" ;;
  --status) mode="status" ;;
  "") ;;
  *) echo "unknown argument: $1" >&2; exit 2 ;;
esac

cd "${repo_root}"
PYTHONPATH="${repo_root}/services/axon-watch${PYTHONPATH:+:${PYTHONPATH}}" \
  python3 - "${mode}" <<'PY'
import json
import sys

from app.tunnel.cloudflared_installer import (
    CloudflaredInstallError,
    install_cloudflared,
    installer_diagnostics,
)

mode = sys.argv[1]
try:
    if mode != "status":
        print(json.dumps(install_cloudflared(force=mode == "force"), indent=2))
    print(json.dumps(installer_diagnostics(), indent=2))
except CloudflaredInstallError as exc:
    print(f"cloudflared install failed: {exc}", file=sys.stderr)
    raise SystemExit(1)
PY
