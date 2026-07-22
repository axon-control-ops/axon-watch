#!/usr/bin/env bash
# Poll Axon-X Fast Gate for the current git branch (or an explicit run id).
# Usage:
#   ./scripts/ops/watch-fast-gate.sh           # watch newest run for this branch
#   ./scripts/ops/watch-fast-gate.sh 29925529734
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${repo_root}"

if ! command -v gh >/dev/null 2>&1; then
  echo "gh CLI is required (https://cli.github.com/)" >&2
  exit 1
fi

run_id="${1:-}"
branch="$(git branch --show-current 2>/dev/null || true)"
if [[ -z "${branch}" ]]; then
  echo "Not on a git branch; pass an explicit run id." >&2
  exit 1
fi

echo "Branch: ${branch}"
echo "Workflow: Axon-X Fast Gate"
echo

if [[ -z "${run_id}" ]]; then
  mapfile -t rows < <(
    gh run list \
      --branch "${branch}" \
      --workflow "Axon-X Fast Gate" \
      --limit 5 \
      --json databaseId,status,conclusion,displayTitle,url,headSha \
      --jq '.[] | [.databaseId, .status, (.conclusion // "-"), .displayTitle, .url] | @tsv'
  )
  if [[ "${#rows[@]}" -eq 0 ]]; then
    echo "No Fast Gate runs found for ${branch}."
    exit 0
  fi
  printf '%s\n' "${rows[@]}" | column -t -s $'\t' || printf '%s\n' "${rows[@]}"
  run_id="$(printf '%s\n' "${rows[0]}" | awk '{print $1}')"
  echo
  echo "Following run ${run_id}…"
fi

gh run watch "${run_id}" --exit-status
echo
gh run view "${run_id}" --json conclusion,url,displayTitle \
  --jq '"\(.displayTitle)\nconclusion=\(.conclusion)\n\(.url)"'
