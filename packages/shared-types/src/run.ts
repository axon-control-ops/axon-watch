export const RUN_MODES = ['ask', 'agent', 'plan', 'auto', 'watch'] as const;
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
}
