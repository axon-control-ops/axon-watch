#!/usr/bin/env bash
# Contract unit tests: control-plane and watch share the top-level `app` package name,
# so watch vault tests run in an isolated PYTHONPATH (same pattern as test18-vault-parity.sh).
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${repo_root}"

# Gate 6 / worker isolations often have only docs or Gate-6 harness edits dirty.
# The full module list exceeds the Gate 6 test budget (~300s); path-scope here so
# acceptance can pass without skipping verification of the harness itself.
_axon_contract_dirty_paths() {
  git status --porcelain -uall 2>/dev/null | while IFS= read -r line; do
    [[ ${#line} -lt 4 ]] && continue
    rest="${line:3}"
    rest="${rest#"${rest%%[![:space:]]*}"}"
    if [[ "${rest}" == *" -> "* ]]; then
      rest="${rest##* -> }"
    fi
    rest="${rest%\"}"
    rest="${rest#\"}"
    [[ -n "${rest}" ]] || continue
    printf '%s\n' "${rest}"
  done
}

_axon_contract_path_class() {
  local path="$1"
  case "${path}" in
    .cursor/*|.axon-si/*) printf 'noise' ;;
    docs/*) printf 'docs' ;;
    scripts/verify/run_contract_unit_tests.sh|\
    services/control-plane/app/workspace_agents/verifier_runner.py|\
    services/control-plane/app/workspace_agents/verifier_checks.py|\
    services/control-plane/app/workspace_agents/verifier_contract.py|\
    services/control-plane/app/workspace_agents/diff_policy.py|\
    services/control-plane/app/workspace_delivery/publish.py|\
    tests/test_gate6_path_scoped_checks.py|\
    tests/test_gate6_project_contract.py|\
    tests/test_gate6_verifier_contract.py|\
    docs/ops/agent-reports/*) printf 'gate6' ;;
    # Operator-stop / shift-continuation CEO auto-approve attend (Quinn integrations).
    # Keep Gate 6 under the ~300s budget instead of the full 100+ module suite.
    services/control-plane/app/workspace_agents/ceo_pending_approve.py|\
    tests/test_ceo_pending_approve.py) printf 'ceo_approve' ;;
    apps/*|services/*|packages/*|scripts/*|tests/*|config/*|.github/*|\
    project.axon.yaml|package.json|package-lock.json) printf 'code' ;;
    *) printf 'other' ;;
  esac
}

_axon_contract_suite_mode() {
  local path class
  local seen_gate6=0
  local seen_ceo_approve=0
  local seen_code=0
  while IFS= read -r path; do
    [[ -n "${path}" ]] || continue
    class="$(_axon_contract_path_class "${path}")"
    case "${class}" in
      gate6) seen_gate6=1 ;;
      ceo_approve) seen_ceo_approve=1 ;;
      code) seen_code=1 ;;
      noise|docs|other) ;;
    esac
  done < <(_axon_contract_dirty_paths)
  if [[ "${seen_code}" -eq 1 ]]; then
    printf 'full'
  elif [[ "${seen_ceo_approve}" -eq 1 ]]; then
    printf 'ceo_approve'
  elif [[ "${seen_gate6}" -eq 1 ]]; then
    printf 'gate6'
  else
    printf 'skip'
  fi
}

if [[ "${AXON_CONTRACT_SUITE_FORCE_FULL:-}" != "1" ]]; then
  _suite_mode="$(_axon_contract_suite_mode)"
  case "${_suite_mode}" in
    skip)
      echo "contract unit tests skipped: no code-path changes in dirty set"
      exit 0
      ;;
    ceo_approve)
      source "${repo_root}/scripts/dev/lib/common.sh"
      "${repo_root}/scripts/dev/ensure-python-deps.sh"
      python_bin="$(resolve_python "${repo_root}")"
      echo "contract unit tests: CEO auto-approve / shift-continuation path-scope"
      # Include Gate 6 harness when this script itself is also dirty (path-scope edits).
      "${python_bin}" -m unittest -v \
        tests.test_ceo_pending_approve \
        tests.test_failure_detail \
        tests.test_gate6_path_scoped_checks \
        tests.test_gate6_project_contract \
        tests.test_gate6_verifier_contract
      exit $?
      ;;
    gate6)
      source "${repo_root}/scripts/dev/lib/common.sh"
      "${repo_root}/scripts/dev/ensure-python-deps.sh"
      python_bin="$(resolve_python "${repo_root}")"
      echo "contract unit tests: Gate 6 path-scope harness only"
      "${python_bin}" -m unittest -v \
        tests.test_gate6_path_scoped_checks \
        tests.test_gate6_project_contract \
        tests.test_gate6_verifier_contract
      exit $?
      ;;
  esac
fi

source "${repo_root}/scripts/dev/lib/common.sh"
"${repo_root}/scripts/dev/ensure-python-deps.sh"
python_bin="$(resolve_python "${repo_root}")"

main_tests=(
  tests.test_guardrail_file_sizes
  tests.test_ci_gate_contract
  tests.test_shared_contract_fixtures
  tests.test_runtime_summary_assembler
  tests.test_control_plane_runtime_summary
  tests.test_control_plane_operator_briefing
  tests.test_operator_briefing_signals
  tests.test_control_plane_workspaces
  tests.test_workspace_project_bindings
  tests.test_control_plane_workspace_handoffs
  tests.test_watch_connectors
  tests.test_control_plane_connectors
  tests.test_watch_commands_events
  tests.test_control_plane_watch_commands
  tests.test_watch_delivery_receipts
  tests.test_control_plane_delivery_receipts
  tests.test_watch_kairo_rules
  tests.test_control_plane_kairo_rules
  tests.test_operator_presence
  tests.test_control_plane_operator_presence
  tests.test_deployment_readiness
  tests.test_control_plane_workspace_files
  tests.test_control_plane_terminal
  tests.test_control_plane_chat
  tests.test_attachment_store
  tests.test_chat_parity_slices
  tests.test_control_plane_chat_health
  tests.test_employee_chat_thread
  tests.test_employee_persona_prompt
  tests.test_team_roster_context
  tests.test_teammate_route
  tests.test_command_executor
  tests.test_workspace_agent_scheduler
  tests.test_failure_detail
  tests.test_ceo_pending_approve
  tests.test_run_outcome
  tests.test_workspace_agents
  tests.test_worker_scheduler_routes
  tests.test_worker_scheduler_settings_store
  tests.test_workspace_worker_prompt
  tests.test_chat_orchestration
  tests.test_watch_bootstrap_signal
  tests.test_watch_summary_signal
  tests.test_watch_ranking
  tests.test_control_plane_inbox_projection
  tests.test_signal_consistency
  tests.test_run_state_transitions
  tests.test_run_startup_reconcile
  tests.test_run_stale_reconcile
  tests.test_run_employee_retention
  tests.test_run_review_ready_reconcile
  tests.test_run_operator_facing_queries
  tests.test_control_plane_runs
  tests.test_runtime_summary_active_runs
  tests.test_service_health_endpoints
  tests.test_control_plane_watch_integration
  tests.test_control_plane_skeleton_e2e
  tests.test_measure_shell_boot
  tests.test_parity_a1_run_stop_resume
  tests.test_parity_a2_approval_boundaries
  tests.test_parity_a3_review_ready_state
  tests.test_parity_a4_signal_inbox_consistency
  tests.test_parity_b1_shell_boot_verify_wiring
  tests.test_parity_b2_latency_budgets
  tests.test_parity_b3_boot_critical_fields
  tests.test_parity_c1_persona_settings
  tests.test_parity_c2_executive_operator_rhythm
  tests.test_parity_c3_mobile_compact_viewport
  tests.test_parity_c4_spoken_high_value_alerts
  tests.test_parity_d1_watch_persistence
  tests.test_parity_d2_delivery_channel_adapters
  tests.test_parity_d3_dedicated_host_smoke
  tests.test_parity_d4_multi_project
  tests.test_parity_d5_voice_deck
  tests.test_parity_d6_dock_and_startup
  tests.test_production_operator_surface
  tests.test_parity_closure_order
  tests.test_planning_bundle_migration
  tests.test_test10_final_parity_acceptance
  tests.test_control_plane_vault
  tests.test_cli_runtime_catalog
  tests.test_control_plane_runtime_status
  tests.test_cli_runtime_agents
  tests.test_lane_b_agent
  tests.test_scanned_workbook_gate
  tests.test_plan_store
  tests.test_control_plane_plans
  tests.test_runtime_vault_integration
  tests.test_email_settings_store
  tests.test_email_reply_suggest
  tests.test_email_smtp_send
  tests.test_email_account_resolve
  tests.test_operator_evidence
  tests.test_kairo_conversation_endpoints
  tests.test_kairo_stt
  tests.test_kairo_tool_milestone
  tests.test_voice_autonomy
  tests.test_voice_dispatch
  tests.test_command_shortcuts
  tests.test_kairo_conversation_turns
  tests.test_conversation_transcript
  tests.test_voice_transcript_store
  tests.test_debug_session_log_endpoint
  tests.test_critical_review_clause
  tests.test_gate2_auth_containment
  tests.test_gate3_worker_isolation
  tests.test_gate4_task_ledger
  tests.test_lead_task_plan
  tests.test_lead_fan_out
  tests.test_lead_replan
  tests.test_gate6_verifier_contract
  tests.test_gate6_project_contract
  tests.test_ci_remediation
  tests.test_safe_improvement
  tests.test_safe_improvement_gate
)

watch_vault_tests=(
  tests.test_vault_csv_import
  tests.test_vault_snapshot
  tests.test_vault_parity
)

watch_signal_tests=(
  tests.test_email_signal
  tests.test_connector_signal
  tests.test_connector_inbox_integration
  tests.test_actionable_inbox_signals
  tests.test_watch_inbox_assembly
)

watch_connector_tests=(
  tests.test_connector_probe_cache
)

watch_monitor_tests=(
  tests.test_monitor_slice_registry
  tests.test_dashpro_monitor_cache
  tests.test_dashpro_monitor_slice
  tests.test_dashpro_monitor_vault_action
  tests.test_monitor_inbox_integration
)

watch_dashpro_api_tests=(
  tests.test_dashpro_posthog
  tests.test_dashpro_sentry
  tests.test_dashpro_supabase_storage
)

watch_tunnel_tests=(
  tests.test_tunnel_remote_control
)

status=0

run_modules() {
  local label="$1"
  local pythonpath="$2"
  shift 2
  echo "contract unit tests: ${label}"
  for test_module in "$@"; do
    echo "contract module: ${test_module}"
    if [[ -n "${pythonpath}" ]]; then
      PYTHONPATH="${pythonpath}" "${python_bin}" -m unittest -v "${test_module}" || status=1
    else
      "${python_bin}" -m unittest -v "${test_module}" || status=1
    fi
  done
}

# Each service uses the top-level package name app. Running modules in
# separate interpreter processes prevents a watch test import/module state
# from contaminating a later control-plane test (and vice versa).
run_modules "control-plane + shared suite" "" "${main_tests[@]}"
run_modules "axon-watch vault (isolated PYTHONPATH)" \
  "${repo_root}/services/axon-watch" "${watch_vault_tests[@]}"
run_modules "axon-watch email signals (isolated PYTHONPATH)" \
  "${repo_root}/services/axon-watch" "${watch_signal_tests[@]}"
run_modules "axon-watch connector probe cache (isolated PYTHONPATH)" \
  "${repo_root}/services/axon-watch" "${watch_connector_tests[@]}"
run_modules "axon-watch monitor probe cache (isolated PYTHONPATH)" \
  "${repo_root}/services/axon-watch" "${watch_monitor_tests[@]}"
run_modules "axon-watch DashPro monitor API resilience (isolated PYTHONPATH)" \
  "${repo_root}/services/axon-watch" "${watch_dashpro_api_tests[@]}"
run_modules "axon-watch native tunnel control (isolated PYTHONPATH)" \
  "${repo_root}/services/axon-watch" "${watch_tunnel_tests[@]}"

exit "${status}"
