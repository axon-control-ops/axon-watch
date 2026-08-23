#!/usr/bin/env bash
# Dispatch Noor (TPS Lead) to build RFQ26052 final submission pack.
set -euo pipefail
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
# shellcheck disable=SC1091
[[ -f "${repo_root}/.env" ]] && source "${repo_root}/.env"
export AXON_WATCH_WORKSPACE_ID="${AXON_WATCH_WORKSPACE_ID:-workspace_tps}"
goal='Package RFQ26052 final email submission: use docs/rfq/OFFICIAL-RFQ26052-MNT240XED-magnetic-name-tag-SUBMISSION.pdf (Lesego signed), run scripts/build-rfq26052-submission-pack.py, verify RFQ26052-FINAL-SUBMISSION-PACK.pdf, update submission-pack doc with page count and file list. Do not include page-4/5 attachment checklists on the RFQ form.'
exec "${repo_root}/scripts/ops/axon-assign.sh" --workspace workspace_tps --mode decompose -- "${goal}"
