import type { OperatorPresence } from './presence';
import type { ApprovalRecord } from './control-plane';
import type {
  CliRuntimeReadiness,
  RuntimeSummaryActiveRun,
  RuntimeSummaryDegradedState,
} from './runtime';
import type { InboxItem } from './signals';

export const BRIEFING_ACTION_KINDS = [
  'approve_run',
  'resume_run',
  'review_signal',
  'inspect_runtime',
] as const;
export type BriefingActionKind = (typeof BRIEFING_ACTION_KINDS)[number];

export interface BriefingAction {
  action_id: string;
  kind: BriefingActionKind;
  title: string;
  detail: string;
  workspace_id: string | null;
  run_id: string | null;
  signal_id: string | null;
}

export interface OperatorBriefingPendingApprovals {
  count: number;
  items: ApprovalRecord[];
}

export interface OperatorBriefingConnectivity {
  control_plane_ready: boolean;
  watch_connected: boolean;
}

export interface ProductionReadinessCheck {
  id: string;
  ok: boolean;
  weight: number;
  detail: string;
}

export interface ProductionReadiness {
  score: number;
  grade: 'not_ready' | 'partial' | 'ready';
  autonomy_mode: 'manual' | 'semi' | 'full';
  blockers: string[];
  checks: ProductionReadinessCheck[];
  summary: string;
}

export interface ExecutiveOperatorRhythm {
  notice: string;
  advise: string;
  decide: string;
  execute: string;
  verify: string;
  report: string;
}

export interface OperatorBriefingScope {
  mode: 'fleet' | 'workspace';
  workspace_id?: string;
}

export interface OperatorBriefingMemoryHighlight {
  memory_id: string;
  workspace_id: string;
  kind: string;
  title: string;
  content: string;
  source_refs: Array<Record<string, unknown>>;
  created_at: string;
  updated_at: string;
  due_at?: string;
  why_now?: string;
  priority?: string;
  status?: string;
}

export interface OperatorBriefing {
  generated_at: string;
  scope?: OperatorBriefingScope;
  notice: string;
  advise: string;
  /** One-click Attend action for the current Advise line (switch workspace + Attention). */
  advise_ui_action?: Record<string, unknown> | null;
  executive_rhythm: ExecutiveOperatorRhythm;
  top_signals: InboxItem[];
  pending_approvals: OperatorBriefingPendingApprovals;
  active_runs: RuntimeSummaryActiveRun[];
  next_safe_actions: BriefingAction[];
  /** review_ready runs + Lead plans awaiting VAXON engagement */
  awaiting_engagement_count?: number;
  degraded: RuntimeSummaryDegradedState;
  cli_runtime?: CliRuntimeReadiness;
  connectivity: OperatorBriefingConnectivity;
  production_readiness?: ProductionReadiness;
  memory_highlights?: OperatorBriefingMemoryHighlight[];
  due_reminders?: OperatorBriefingMemoryHighlight[];
  host_artifacts?: Array<Record<string, unknown>>;
  operator_presence?: OperatorPresence;
}
