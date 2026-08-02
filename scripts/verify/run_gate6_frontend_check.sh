#!/usr/bin/env bash
# Gate 6 frontend check wrapper: skip vue-tsc/vite when the worker diff has no
# console-web paths. Full frontend verify remains on Fast Gate / CI.
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${repo_root}"

check_name="${1:-typecheck}"
case "${check_name}" in
  typecheck)
    command=(npm run typecheck --workspace=apps/console-web)
    ;;
  build)
    command=(npm run build --workspace=apps/console-web)
    ;;
  *)
    echo "usage: $0 typecheck|build" >&2
    exit 2
    ;;
esac

frontend_hit="$(
  git status --porcelain -uall 2>/dev/null | awk '{
    path=$2
    if (NF >= 3 && $1 ~ /R|C/) path=$NF
    if (path ~ /^apps\/console-web\//) { print path; exit }
  }'
)"

if [[ -z "${frontend_hit}" ]]; then
  echo "gate6 ${check_name}: skip (no apps/console-web changes in worker diff)"
  exit 0
fi

echo "gate6 ${check_name}: running for ${frontend_hit}"
exec "${command[@]}"
