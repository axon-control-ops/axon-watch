import type { RunMode, RunPhase, RunStatus } from './run';
import type { SignalSeverity, SignalView } from './signals';

export interface RuntimeSummaryControlPlane {
  status: string;
  version: string;
  uptime_seconds: number;
  ready: boolean;
}

export interface RuntimeSummaryWatch {
  status: string;
  connected: boolean;
  last_summary_at: string;
  degraded_reason: string | null;
}

export interface RuntimeIdentity {
  provider_family: string;
  provider_name: string;
  model_name: string;
  mode_default: RunMode;
  tool_calling_supported: boolean;
  reasoning_supported: boolean;
}

export interface RuntimeSummaryActiveRun {
  run_id: string;
  workspace_id: string;
  mode: RunMode;
  status: RunStatus;
  phase: RunPhase;
  title: string;
  detail: string;
  lane_id: string;
  updated_at: string;
}

export interface RuntimeSummaryApprovals {
  pending_count: number;
  highest_severity: SignalSeverity | null;
  latest_approval_at: string | null;
}

export interface RuntimeSummarySignals {
  open_count: number;
  critical_count: number;
  high_count: number;
  top_items: SignalView[];
  last_updated_at: string;
}

export interface RuntimeSummaryCapabilities {
  editor: boolean;
  terminal: boolean;
  browser_preview: boolean;
  watch_connected: boolean;
  approvals_enabled: boolean;
  notifications_enabled: boolean;
}

export interface RuntimeSummaryDegradedState {
  active: boolean;
  reasons: string[];
}

export interface CliRuntimeReadiness {
  dispatch_ready: boolean;
  ready_count: number;
  local_count: number;
  default_runtime: string;
  default_ready: boolean;
  blockers: string[];
}

export interface RuntimeSummaryConnectors {
  configured: number;
  ok: number;
  degraded: number;
  unavailable: number;
  required_unavailable: number;
  last_updated_at: string;
}

export interface RuntimeSummary {
  generated_at: string;
  control_plane: RuntimeSummaryControlPlane;
  watch: RuntimeSummaryWatch;
  runtime_identity: RuntimeIdentity;
  active_runs: RuntimeSummaryActiveRun[];
  approvals: RuntimeSummaryApprovals;
  signals: RuntimeSummarySignals;
  connectors: RuntimeSummaryConnectors;
  capabilities: RuntimeSummaryCapabilities;
  degraded: RuntimeSummaryDegradedState;
  cli_runtime?: CliRuntimeReadiness;
}
