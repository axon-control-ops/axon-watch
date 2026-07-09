#!/usr/bin/env bash
# Contract unit tests: control-plane and watch share the top-level `app` package name,
# so watch vault tests run in an isolated PYTHONPATH (same pattern as test18-vault-parity.sh).
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${repo_root}"

source "${repo_root}/scripts/dev/lib/common.sh"
"${repo_root}/scripts/dev/ensure-python-deps.sh"
python_bin="$(resolve_python "${repo_root}")"

main_tests=(
  tests.test_guardrail_file_sizes
  tests.test_shared_contract_fixtures
  tests.test_runtime_summary_assembler
  tests.test_control_plane_runtime_summary
  tests.test_control_plane_operator_briefing
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
  tests.test_command_executor
  tests.test_chat_orchestration
  tests.test_watch_bootstrap_signal
  tests.test_watch_summary_signal
  tests.test_watch_ranking
  tests.test_control_plane_inbox_projection
  tests.test_signal_consistency
  tests.test_run_state_transitions
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
  tests.test_runtime_vault_integration
)

watch_vault_tests=(
  tests.test_vault_csv_import
  tests.test_vault_snapshot
  tests.test_vault_parity
)

echo "contract unit tests: control-plane + shared suite"
"${python_bin}" -m unittest "${main_tests[@]}"

echo "contract unit tests: axon-watch vault (isolated PYTHONPATH)"
PYTHONPATH="${repo_root}/services/axon-watch" "${python_bin}" -m unittest "${watch_vault_tests[@]}"
