#!/usr/bin/env bash
# Fallback Gate 9 poller when GitHub webhooks cannot reach control-plane.
# Usage:
#   CONTROL_PLANE_URL=http://127.0.0.1:8787 ./scripts/ops/poll-fast-gate-remediation.sh
# Posts a synthetic completed workflow_run payload for the latest Fast Gate run
# on the current branch (requires gh + jq + curl). Red runs start remediation;
# green runs clear stale failure state. Prefer the real webhook in production.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

env_file="${AXON_WATCH_DEPLOYMENT_ENV:-${HOME}/.config/axon-watch/deployment.env}"
if [[ ! -f "$env_file" && -f /etc/axon-watch/deployment.env ]]; then
  env_file=/etc/axon-watch/deployment.env
fi
if [[ -f "$env_file" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "$env_file"
  set +a
fi

CP_URL="${CONTROL_PLANE_URL:-http://127.0.0.1:8787}"
SECRET="${AXON_WATCH_GITHUB_WEBHOOK_SECRET:-${GITHUB_WEBHOOK_SECRET:-}}"
BRANCH="$(git branch --show-current)"

if [[ -z "$SECRET" ]]; then
  echo "Set AXON_WATCH_GITHUB_WEBHOOK_SECRET (or GITHUB_WEBHOOK_SECRET)." >&2
  exit 1
fi

RUN_JSON="$(gh run list --branch "$BRANCH" --workflow "Axon-X Fast Gate" --limit 1 --json databaseId,conclusion,headSha,displayTitle,url,status,name,headBranch)"
CONCLUSION="$(echo "$RUN_JSON" | jq -r '.[0].conclusion // empty')"
STATUS="$(echo "$RUN_JSON" | jq -r '.[0].status // empty')"
if [[ "$STATUS" != "completed" ]]; then
  echo "Latest Fast Gate on $BRANCH is not completed (status=${STATUS:-missing})."
  exit 0
fi
if [[ "$CONCLUSION" != "failure" && "$CONCLUSION" != "success" ]]; then
  echo "Latest Fast Gate on $BRANCH is not actionable (conclusion=${CONCLUSION:-missing})."
  exit 0
fi

RUN_ID="$(echo "$RUN_JSON" | jq -r '.[0].databaseId')"
HEAD_SHA="$(echo "$RUN_JSON" | jq -r '.[0].headSha')"
HEAD_BRANCH="$(echo "$RUN_JSON" | jq -r '.[0].headBranch // empty')"
TITLE="$(echo "$RUN_JSON" | jq -r '.[0].displayTitle // empty')"
URL="$(echo "$RUN_JSON" | jq -r '.[0].url')"
NAME="$(echo "$RUN_JSON" | jq -r '.[0].name // "Axon-X Fast Gate"')"

OWNER="$(gh repo view --json owner -q .owner.login)"
REPO="$(gh repo view --json name -q .name)"

BODY="$(jq -nc \
  --arg id "$RUN_ID" \
  --arg name "$NAME" \
  --arg branch "${HEAD_BRANCH:-$BRANCH}" \
  --arg sha "$HEAD_SHA" \
  --arg url "$URL" \
  --arg title "$TITLE" \
  --arg owner "$OWNER" \
  --arg repo "$REPO" \
  --arg conclusion "$CONCLUSION" \
  '{
    action: "completed",
    workflow_run: {
      id: ($id|tonumber),
      name: $name,
      status: "completed",
      conclusion: $conclusion,
      head_branch: $branch,
      head_sha: $sha,
      html_url: $url,
      display_title: $title,
      path: ".github/workflows/fast-gate.yml"
    },
    repository: {
      name: $repo,
      full_name: ($owner + "/" + $repo),
      owner: { login: $owner }
    }
  }')"

SIG="sha256=$(printf '%s' "$BODY" | openssl dgst -sha256 -hmac "$SECRET" | awk '{print $2}')"

curl -fsS -X POST "$CP_URL/api/webhooks/github/workflow-run" \
  -H "Content-Type: application/json" \
  -H "X-GitHub-Event: workflow_run" \
  -H "X-Hub-Signature-256: $SIG" \
  -d "$BODY"
echo
