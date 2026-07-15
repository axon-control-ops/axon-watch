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

export interface OperatorEvidenceRecord {
  node_id: string;
  kind: string;
  title: string;
  summary: string;
  facts: Array<{ label: string; value: string }>;
  sources: Array<{ ref_type: string; ref_id: string; label: string; workspace_id?: string }>;
  actions: Array<{
    label: string;
    target: 'workspace' | 'signal' | 'handoff' | string;
    workspace_id?: string;
    signal_id?: string;
  }>;
  sections: Array<{
    title: string;
    items: Array<{
      title: string;
      detail: string;
      source_ref?: { ref_type: string; ref_id: string; label: string; workspace_id?: string };
    }>;
  }>;
}

export interface OperatorMemoryRecord {
  memory_id: string;
  workspace_id: string;
  scope: string;
  kind: string;
  title: string;
  content: string;
  source_refs: Array<Record<string, unknown>>;
  created_at: string;
  updated_at: string;
}

export async function fetchOperatorBriefing(options?: {
  viewportCompact?: boolean;
  workspaceId?: string | null;
  light?: boolean;
}): Promise<OperatorBriefing> {
  const compact = Boolean(options?.viewportCompact);
  const params = new URLSearchParams();
  if (compact) {
    params.set('viewport_compact', 'true');
  }
  if (options?.light) {
    params.set('light', 'true');
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

export async function fetchOperatorEvidence(nodeId: string): Promise<OperatorEvidenceRecord> {
  const params = new URLSearchParams({ node_id: nodeId });
  return fetchJson<OperatorEvidenceRecord>(
    `/api/operator/evidence?${params.toString()}`,
    {},
    'operator evidence request failed',
  );
}

export async function fetchOperatorMemories(options?: {
  workspaceId?: string | null;
  query?: string;
  kind?: string;
  limit?: number;
}): Promise<{ items: OperatorMemoryRecord[]; count: number }> {
  const params = new URLSearchParams();
  if (options?.workspaceId?.trim()) {
    params.set('workspace_id', options.workspaceId.trim());
  }
  if (options?.query?.trim()) {
    params.set('query', options.query.trim());
  }
  if (options?.kind?.trim()) {
    params.set('kind', options.kind.trim());
  }
  if (options?.limit) {
    params.set('limit', String(options.limit));
  }
  const query = params.size ? `?${params.toString()}` : '';
  return fetchJson<{ items: OperatorMemoryRecord[]; count: number }>(
    `/api/operator/memories${query}`,
    {},
    'operator memories request failed',
  );
}

export async function createOperatorMemory(body: {
  workspace_id?: string;
  scope?: string;
  kind?: string;
  title: string;
  content: string;
  source_refs?: Array<Record<string, unknown>>;
}): Promise<{ item: OperatorMemoryRecord }> {
  return fetchJson<{ item: OperatorMemoryRecord }>(
    '/api/operator/memories',
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    },
    'operator memory save failed',
  );
}

export async function captureOperatorResearch(body: {
  workspace_id?: string;
  title?: string;
  query?: string;
  url?: string;
  source_refs?: Array<Record<string, unknown>>;
}): Promise<{ result: Record<string, unknown>; memory: OperatorMemoryRecord }> {
  return fetchJson<{ result: Record<string, unknown>; memory: OperatorMemoryRecord }>(
    '/api/operator/research/capture',
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    },
    'operator research capture failed',
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
