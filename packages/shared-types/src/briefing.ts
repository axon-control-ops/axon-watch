import type { OperatorPresence } from './presence';
import type { ApprovalRecord } from './control-plane';
import type { RuntimeSummaryActiveRun, RuntimeSummaryDegradedState } from './runtime';
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

export interface ExecutiveOperatorRhythm {
  notice: string;
  advise: string;
  decide: string;
  execute: string;
  verify: string;
  report: string;
}

export interface OperatorBriefing {
  generated_at: string;
  notice: string;
  advise: string;
  executive_rhythm: ExecutiveOperatorRhythm;
  top_signals: InboxItem[];
  pending_approvals: OperatorBriefingPendingApprovals;
  active_runs: RuntimeSummaryActiveRun[];
  next_safe_actions: BriefingAction[];
  degraded: RuntimeSummaryDegradedState;
  connectivity: OperatorBriefingConnectivity;
  operator_presence?: OperatorPresence;
}
