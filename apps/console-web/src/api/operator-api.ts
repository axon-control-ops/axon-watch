import type { OperatorBriefing, OperatorPresenceSettings, RuntimeSummary } from '../contracts/canonical';

import type { BrainGraphSnapshot } from '../lib/operator-brain-graph-view';

import { fetchJson } from './client';

export type FleetHealthSnapshot = {
  generated_at: string;
  watch_connected: boolean;
  connectors: RuntimeSummary['connectors'];
  degraded: RuntimeSummary['degraded'];
  items: Array<{
    workspace_id: string;
    display_name: string;
    connection_kind: string;
    health: 'nominal' | 'attention' | 'critical';
    active_runs: number;
    review_ready_count: number;
    executing_count: number;
    pending_approvals_count: number;
    open_signals_count: number;
    critical_signals_count: number;
    top_signal_title: string | null;
  }>;
  count: number;
};

export interface OperatorPresenceSettingsSnapshot {
  settings: OperatorPresenceSettings;
  updated_at?: string;
}

export async function fetchOperatorBriefing(options?: {
  viewportCompact?: boolean;
  workspaceId?: string | null;
}): Promise<OperatorBriefing> {
  const compact = Boolean(options?.viewportCompact);
  const params = new URLSearchParams();
  if (compact) {
    params.set('viewport_compact', 'true');
  }
  const workspaceId = options?.workspaceId?.trim();
  if (workspaceId) {
    params.set('workspace_id', workspaceId);
  }
  const query = params.size > 0 ? `?${params.toString()}` : '';
  return fetchJson<OperatorBriefing>(
    `/api/briefing${query}`,
    {},
    'operator briefing request failed',
  );
}

export async function fetchOperatorFleetHealth(): Promise<FleetHealthSnapshot> {
  return fetchJson<FleetHealthSnapshot>(
    '/api/operator/fleet-health',
    {},
    'operator fleet health request failed',
  );
}

export async function fetchOperatorBrainGraph(): Promise<BrainGraphSnapshot> {
  return fetchJson<BrainGraphSnapshot>(
    '/api/operator/brain-graph',
    {},
    'operator brain graph request failed',
  );
}

export async function fetchOperatorPresenceSettings(): Promise<OperatorPresenceSettingsSnapshot> {
  return fetchJson<OperatorPresenceSettingsSnapshot>(
    '/api/operator-presence/settings',
    {},
    'operator presence settings request failed',
  );
}

export async function saveOperatorPresenceSettings(
  patch: Partial<OperatorPresenceSettings>,
): Promise<OperatorPresenceSettingsSnapshot> {
  return fetchJson<OperatorPresenceSettingsSnapshot>(
    '/api/operator-presence/settings',
    {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(patch),
    },
    'operator presence settings save failed',
  );
}
