#!/usr/bin/env bash
# Fallback Gate 9 poller for DashPro workflows when GitHub webhooks cannot reach
# the local control plane. Ingests the latest completed run per bound workflow.
#
# Usage:
#   CONTROL_PLANE_URL=http://127.0.0.1:8787 ./scripts/ops/poll-dashpro-ci-remediation.sh
# Optional:
#   DASHPRO_CI_BRANCH=worker/run_24cb629982b3  # default: latest open draft PR head
#   DASHPRO_CI_REPO=axon-control-ops/dashpro
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

export PATH="${HOME}/.local/bin:/usr/local/bin:${PATH}"

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
REPO="${DASHPRO_CI_REPO:-axon-control-ops/dashpro}"
CONFIG="${AXON_WATCH_CI_REMEDIATION_FILE:-$ROOT/config/ci-remediation.json}"

if [[ -z "$SECRET" ]]; then
  echo "Set AXON_WATCH_GITHUB_WEBHOOK_SECRET (or GITHUB_WEBHOOK_SECRET)." >&2
  exit 1
fi

# shellcheck disable=SC1091
source "$ROOT/scripts/ops/lib/poll-ci-remediation-post.sh"

BRANCH="${DASHPRO_CI_BRANCH:-}"
if [[ -z "$BRANCH" ]]; then
  BRANCH="$(gh pr list --repo "$REPO" --state open --json headRefName --limit 1 \
    | jq -r '.[0].headRefName // empty')"
fi
if [[ -z "$BRANCH" ]]; then
  BRANCH="development"
fi

mapfile -t WORKFLOWS < <(
  jq -r '
    .bindings[]
    | select(.enabled == true and .workspace_id == "workspace_dashpro")
    | .workflow_name
  ' "$CONFIG"
)

if [[ "${#WORKFLOWS[@]}" -eq 0 ]]; then
  echo "No enabled DashPro CI bindings in $CONFIG"
  exit 0
fi

echo "Polling DashPro CI on $REPO branch=$BRANCH → $CP_URL"

posted=0
skipped=0
for workflow in "${WORKFLOWS[@]}"; do
  RUN_JSON="$(gh run list --repo "$REPO" --branch "$BRANCH" --workflow "$workflow" \
    --limit 1 --json databaseId,conclusion,headSha,displayTitle,url,status,name,headBranch 2>/dev/null || echo '[]')"
  STATUS="$(echo "$RUN_JSON" | jq -r '.[0].status // empty')"
  CONCLUSION="$(echo "$RUN_JSON" | jq -r '.[0].conclusion // empty')"
  if [[ "$STATUS" != "completed" ]]; then
    echo "  skip $workflow — not completed (status=${STATUS:-missing})"
    skipped=$((skipped + 1))
    continue
  fi
  if [[ "$CONCLUSION" != "failure" && "$CONCLUSION" != "success" ]]; then
    echo "  skip $workflow — not actionable (conclusion=${CONCLUSION:-missing})"
    skipped=$((skipped + 1))
    continue
  fi

  RUN_ID="$(echo "$RUN_JSON" | jq -r '.[0].databaseId')"
  HEAD_SHA="$(echo "$RUN_JSON" | jq -r '.[0].headSha')"
  HEAD_BRANCH="$(echo "$RUN_JSON" | jq -r '.[0].headBranch // empty')"
  TITLE="$(echo "$RUN_JSON" | jq -r '.[0].displayTitle // empty')"
  URL="$(echo "$RUN_JSON" | jq -r '.[0].url')"
  NAME="$(echo "$RUN_JSON" | jq -r '.[0].name // empty')"

  OWNER="${REPO%%/*}"
  REPO_NAME="${REPO##*/}"

  BODY="$(jq -nc \
    --arg id "$RUN_ID" \
    --arg name "$NAME" \
    --arg branch "${HEAD_BRANCH:-$BRANCH}" \
    --arg sha "$HEAD_SHA" \
    --arg url "$URL" \
    --arg title "$TITLE" \
    --arg owner "$OWNER" \
    --arg repo "$REPO_NAME" \
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
        display_title: $title
      },
      repository: {
        name: $repo,
        full_name: ($owner + "/" + $repo),
        owner: { login: $owner }
      }
    }')"

  echo "  ingest $workflow — $CONCLUSION run=$RUN_ID"
  poll_ci_remediation_post "$CP_URL" "$SECRET" "$BODY"
  posted=$((posted + 1))
done

echo "Done: posted=$posted skipped=$skipped branch=$BRANCH"
