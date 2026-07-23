#!/usr/bin/env bash
# Staging rollback helper referenced by project.axon.yaml.
# Operator/CI should pass previous artifact id; this script records intent only.
set -euo pipefail
PREV="${1:-}"
if [[ -z "$PREV" ]]; then
  echo "usage: $0 <previous-artifact-id>" >&2
  exit 2
fi
echo "rollback-staging: restoring artifact $PREV"
exit 0
