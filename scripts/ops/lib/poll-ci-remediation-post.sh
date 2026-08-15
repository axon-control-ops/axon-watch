#!/usr/bin/env bash
# Shared signed POST helper for Gate 9 workflow_run ingest.
poll_ci_remediation_post() {
  local cp_url="$1"
  local secret="$2"
  local body="$3"

  if [[ -z "$cp_url" || -z "$secret" || -z "$body" ]]; then
    echo "poll_ci_remediation_post: cp_url, secret, and body are required" >&2
    return 1
  fi

  local sig
  sig="sha256=$(printf '%s' "$body" | openssl dgst -sha256 -hmac "$secret" | awk '{print $2}')"

  curl -fsS -X POST "$cp_url/api/webhooks/github/workflow-run" \
    -H "Content-Type: application/json" \
    -H "X-GitHub-Event: workflow_run" \
    -H "X-Hub-Signature-256: $sig" \
    -d "$body"
  echo
}
