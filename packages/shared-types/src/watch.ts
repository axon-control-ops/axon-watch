import type { InboxItem } from './signals';

export interface WatchInboxSnapshot {
  items: InboxItem[];
  count: number;
  updated_at: string;
}

export interface WatchConnectorRecord {
  connector_id: string;
  display_name: string;
  health_url: string;
  required: boolean;
  workspace_id: string;
  status: 'ok' | 'degraded' | 'unavailable' | string;
  last_checked_at: string;
  detail?: string;
  latency_ms?: number;
}

export interface WatchConnectorsSnapshot {
  configured: number;
  ok: number;
  degraded: number;
  unavailable: number;
  required_unavailable: number;
}

export interface WatchObservationSnapshot {
  events_count: number;
  last_event_at: string;
  last_event_type?: string;
  last_command_id?: string;
  last_command_status?: string;
  last_command_at?: string;
  last_command_detail?: string;
  receipts_count?: number;
  last_receipt_at?: string;
  last_receipt_result?: string;
}

export interface WatchSummary {
  status: string;
  signals: Record<string, unknown>;
  inbox: WatchInboxSnapshot;
  connectors: WatchConnectorsSnapshot;
  runtime: Record<string, unknown>;
  observation?: WatchObservationSnapshot;
  updated_at: string;
}

export interface WatchCommandRequest {
  command_id: string;
  command_type: string;
  target_type: string;
  target_id: string;
  requested_by: string;
  payload: Record<string, unknown>;
  requested_at: string;
}

export interface WatchCommandRecord {
  command_id: string;
  command_type: string;
  target_type: string;
  target_id: string;
  requested_by: string;
  requested_at: string;
  status: string;
  updated_at: string;
  receipt: Record<string, unknown>;
}

export interface WatchObservationEvent {
  event_id: string;
  event_type: string;
  occurred_at: string;
  command_id?: string;
  payload: Record<string, unknown>;
}

export interface WatchCommandReceipt {
  accepted: boolean;
  command_id: string;
  status: string;
  receipt: Record<string, unknown>;
}
