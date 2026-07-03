import type { InboxItem } from './signals';

export interface WatchInboxSnapshot {
  items: InboxItem[];
  count: number;
  updated_at: string;
}

export interface WatchSummary {
  status: string;
  signals: Record<string, unknown>;
  inbox: WatchInboxSnapshot;
  connectors: Record<string, unknown>;
  runtime: Record<string, unknown>;
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

export interface WatchCommandReceipt {
  accepted: boolean;
  command_id: string;
  status: string;
  receipt: Record<string, unknown>;
}
