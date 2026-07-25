export const HOST_ACTION_TIERS = ['auto', 'confirm', 'deny'] as const;
export type HostActionTier = (typeof HOST_ACTION_TIERS)[number];

export const DESKTOP_RUNTIMES = ['browser', 'desktop'] as const;
export type DesktopRuntime = (typeof DESKTOP_RUNTIMES)[number];

export interface HostDeviceRecord {
  device_id: string;
  hostname: string;
  platform: string;
  last_seen_at: string;
  capabilities: string[];
  status: string;
}

export interface HostArtifactRecord {
  artifact_id: string;
  device_id: string;
  path: string;
  title: string;
  kind: string;
  mime_type: string;
  origin: string;
  sensitivity: string;
  modified_at: string;
  size_bytes: number;
  thumbnail_local: boolean;
  workspace_id: string;
  meta: Record<string, unknown>;
}

export interface HostEventRecord {
  event_id: string;
  device_id: string;
  kind: string;
  title: string;
  detail: string;
  occurred_at: string;
  artifact_id: string;
  sensitivity: string;
  meta: Record<string, unknown>;
}

export interface HostActionReceipt {
  receipt_id: string;
  device_id: string;
  command_id: string;
  action: string;
  tier: HostActionTier | string;
  status: string;
  result_summary: string;
  created_at: string;
  meta: Record<string, unknown>;
}

export interface HostCapabilitiesSnapshot {
  runtime: DesktopRuntime | string;
  awareness_paused: boolean;
  devices: HostDeviceRecord[];
  latest_snapshot: Record<string, unknown> | null;
  action_tiers: Record<string, string>;
  retention_days: number;
}

export interface OperatorReminderRecord {
  memory_id: string;
  workspace_id: string;
  scope: string;
  kind: string;
  title: string;
  content: string;
  due_at?: string;
  snoozed_until?: string;
  trigger?: string;
  priority?: string;
  status?: string;
  last_presented_at?: string;
  dismiss_reason?: string;
  why_now?: string;
  created_at: string;
  updated_at: string;
}
