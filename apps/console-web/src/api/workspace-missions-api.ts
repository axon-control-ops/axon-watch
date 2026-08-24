import type { WorkspaceMission, WorkspaceImpactEdge } from '../../../../packages/shared-types/src';

import { fetchJson } from './client';

export type WorkspaceMissionImpactPreview = {
  source_workspace_id: string;
  goal: string;
  changed_paths: string[];
  edges: WorkspaceImpactEdge[];
  actionable_count: number;
  review_count: number;
};

export async function previewWorkspaceMissionImpact(input: {
  source_workspace_id: string;
  goal?: string;
  changed_paths?: string[];
}): Promise<WorkspaceMissionImpactPreview> {
  return fetchJson('/api/workspace-missions/impact-preview', {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(input),
  }, 'workspace mission impact preview failed');
}

export async function createWorkspaceMission(input: {
  source_workspace_id: string;
  goal: string;
  risk?: string;
  source_task_id?: string;
  source_run_id?: string;
  changed_paths?: string[];
}): Promise<WorkspaceMission> {
  return fetchJson('/api/workspace-missions', {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(input),
  }, 'workspace mission creation failed');
}

export async function listWorkspaceMissions(status?: string): Promise<WorkspaceMission[]> {
  const query = status ? `?status=${encodeURIComponent(status)}` : '';
  const result = await fetchJson<{ items: WorkspaceMission[] }>(
    `/api/workspace-missions${query}`, {}, 'workspace mission list failed',
  );
  return result.items;
}

export async function runWorkspaceMissionAction(
  missionId: string,
  action: 'retry' | 'cancel' | 'verify' | 'promote',
): Promise<WorkspaceMission> {
  return fetchJson(`/api/workspace-missions/${encodeURIComponent(missionId)}/${action}`, {
    method: 'POST',
  }, `workspace mission ${action} failed`);
}
