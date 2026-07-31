#!/usr/bin/env bash
# Console-web gate: CSS imports, typecheck, Vitest, production build.
# Uses pipefail so a piped failure (e.g. `| tail`) cannot mask a non-zero exit.
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${repo_root}"

npm run verify:css-imports
npm run typecheck -w @axon-watch/console-web
npm run test -w @axon-watch/console-web
npm run build -w @axon-watch/console-web

echo "VERIFY-CONSOLE-WEB PASS"
