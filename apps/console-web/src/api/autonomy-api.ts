import { fetchJson } from './client';

export type AutonomyReceipt = {
  receipt_id: string;
  workspace_id: string;
  kind: string;
  decision: string;
  tier: string;
  risk: string;
  title: string;
  detail: string;
  dedupe_key: string;
  task_id: string | null;
  ask_operator: boolean;
  status: 'pending' | 'resolved' | 'recorded' | string;
  resolution: 'approved' | 'rejected' | '' | string;
  resolved_at: string | null;
  payload?: Record<string, unknown>;
  created_at: string;
};

export type AutonomyStatusFeed = {
  autonomy_mode: 'manual' | 'semi' | 'full';
  autonomous_enabled: boolean;
  effective_autonomy: boolean;
  scheduler: {
    effective_enabled: boolean;
    scheduler_enabled: boolean;
    blocked_by_env: boolean;
    env_allowed: boolean;
    executing_count: number;
    hard_killed?: boolean;
  };
  last_scan: {
    workspace_id?: string;
    scanned_at?: string;
    checked_workspaces?: string[];
    created_count?: number;
    escalated_count?: number;
    skipped_count?: number;
  };
  pending_critical_count: number;
  pending_critical_decisions: AutonomyReceipt[];
  recent_receipts: AutonomyReceipt[];
  safety_contract: {
    auto_allowed: string[];
    requires_operator: string[];
  };
};

export function fetchAutonomyStatus(workspaceId?: string | null): Promise<AutonomyStatusFeed> {
  const cleaned = workspaceId?.trim();
  const query = cleaned ? `?workspace_id=${encodeURIComponent(cleaned)}` : '';
  return fetchJson<AutonomyStatusFeed>(
    `/api/operator/autonomy/status${query}`,
    {},
    'operator autonomy status request failed',
  );
}

export function triggerAutonomyScan(): Promise<Record<string, unknown>> {
  return fetchJson<Record<string, unknown>>(
    '/api/operator/autonomy/scan',
    { method: 'POST' },
    'operator autonomy scan failed',
  );
}

export function resolveAutonomyDecision(
  receiptId: string,
  resolution: 'approved' | 'rejected',
): Promise<AutonomyReceipt> {
  return fetchJson<AutonomyReceipt>(
    `/api/operator/autonomy/decisions/${encodeURIComponent(receiptId)}`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ resolution }),
    },
    'operator autonomy decision failed',
  );
}
