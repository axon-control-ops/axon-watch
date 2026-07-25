export const RUN_MODES = ['ask', 'agent', 'plan', 'debug', 'auto', 'watch'] as const;
export type RunMode = (typeof RUN_MODES)[number];

export const RUN_PHASES = [
  'queued',
  'starting',
  'planning',
  'awaiting_input',
  'awaiting_approval',
  'executing',
  'waiting_external',
  'paused',
  'review_ready',
  'completed',
  'failed',
  'cancelled',
] as const;
export type RunPhase = (typeof RUN_PHASES)[number];

export const RUN_STATUSES = [
  'running',
  'waiting',
  'blocked',
  'review',
  'done',
  'error',
  'stopped',
] as const;
export type RunStatus = (typeof RUN_STATUSES)[number];

/** Worker code-delivery pipeline stages (git/PR/CI — not notification DeliveryReceipt). */
export const WORKER_DELIVERY_STAGES = [
  'changed',
  'verified',
  'committed',
  'pushed',
  'pr_open',
  'ci_pending',
  'ci_green',
  'ci_red',
  'repairing',
  'escalated',
  'blocked',
  'no_change',
] as const;
export type WorkerDeliveryStage = (typeof WORKER_DELIVERY_STAGES)[number];

export interface WorkerDeliveryRefs {
  worker_branch?: string | null;
  commit_sha?: string | null;
  draft_pr_url?: string | null;
  ci_run_url?: string | null;
  ci_conclusion?: string | null;
  attempt?: number | null;
  blocker?: string | null;
}

export interface RunHistoryReceipt {
  type: string;
  summary: string;
  stage?: WorkerDeliveryStage | null;
  refs?: WorkerDeliveryRefs | null;
}

export interface RunRecord {
  run_id: string;
  workspace_id: string;
  lane_id: string;
  mode: RunMode;
  status: RunStatus;
  phase: RunPhase;
  summary: string;
  detail: string;
  started_at: string;
  updated_at: string;
  ended_at: string | null;
  can_stop: boolean;
  can_resume: boolean;
  can_approve: boolean;
  can_review: boolean;
  current_step: string | null;
  history_ref: string;
  /** Roster role that owns this run when started by the continuous worker scheduler. */
  employee_role?: string | null;
  /** Latest worker delivery stage when this run published code. */
  delivery_stage?: WorkerDeliveryStage | null;
  delivery_refs?: WorkerDeliveryRefs | null;
}
