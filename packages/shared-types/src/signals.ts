export const SIGNAL_EVENT_TYPES = [
  'signal_opened',
  'signal_updated',
  'signal_escalated',
  'signal_deescalated',
  'signal_resolved',
  'signal_reopened',
  'delivery_attempted',
  'delivery_succeeded',
  'delivery_failed',
  'operator_acknowledged',
  'operator_dispatched',
  'operator_ignored',
] as const;
export type SignalEventType = (typeof SIGNAL_EVENT_TYPES)[number];

export const SIGNAL_SEVERITIES = ['info', 'warning', 'high', 'critical'] as const;
export type SignalSeverity = (typeof SIGNAL_SEVERITIES)[number];

export const SIGNAL_STATUSES = [
  'open',
  'watching',
  'acknowledged',
  'suppressed',
  'resolved',
  'failed_delivery',
] as const;
export type SignalStatus = (typeof SIGNAL_STATUSES)[number];

export const SIGNAL_SOURCES = [
  'runtime',
  'watch',
  'ci',
  'git',
  'connector',
  'email',
  'workspace',
  'browser',
  'terminal',
  'approval',
  'deployment',
  'manual',
] as const;
export type SignalSource = (typeof SIGNAL_SOURCES)[number];

export const SIGNAL_ACTION_TYPES = [
  'open_dashboard',
  'open_workspace',
  'open_approvals',
  'review_changes',
  'retry',
  'investigate',
  'dispatch',
  'resolve',
  'none',
] as const;
export type SignalActionType = (typeof SIGNAL_ACTION_TYPES)[number];

export const DELIVERY_STATES = [
  'pending',
  'attempted',
  'delivered',
  'failed',
  'suppressed',
  'not_required',
] as const;
export type DeliveryState = (typeof DELIVERY_STATES)[number];

export interface SignalEvent {
  event_id: string;
  signal_id: string;
  event_type: SignalEventType;
  source: SignalSource;
  workspace_id: string;
  project_id: string;
  severity: SignalSeverity;
  status: SignalStatus;
  title: string;
  body: string;
  summary: string;
  created_at: string;
  updated_at: string;
  occurred_at: string;
  dedupe_key: string;
  action_type: SignalActionType;
  action_payload: Record<string, unknown>;
  correlation_ref: string;
  delivery_state: DeliveryState;
  meta: Record<string, unknown>;
}

export interface SignalView {
  signal_id: string;
  workspace_id: string;
  title: string;
  summary: string;
  severity: SignalSeverity;
  status: SignalStatus;
  source: SignalSource;
  created_at: string;
  updated_at: string;
  action_type: SignalActionType;
}

export type InboxItem = SignalView;
