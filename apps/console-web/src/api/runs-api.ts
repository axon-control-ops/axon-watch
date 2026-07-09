import type { RunRecord } from '../contracts/canonical';

import type { RunHistorySnapshot } from '../lib/run-history-view';

import { fetchJson } from './client';

export interface RunListSnapshot {
  items: RunRecord[];
  count: number;
}

export interface CreateRunRequest {
  workspace_id: string;
  mode?: RunRecord['mode'];
  summary: string;
  detail?: string;
  requires_approval?: boolean;
}

export async function fetchRuns(): Promise<RunListSnapshot> {
  return fetchJson<RunListSnapshot>('/api/runs', {}, 'runs request failed');
}

export async function fetchRun(runId: string): Promise<RunRecord> {
  return fetchJson<RunRecord>(`/api/runs/${runId}`, {}, 'run request failed');
}

export async function fetchRunHistory(runId: string): Promise<RunHistorySnapshot> {
  const encodedRunId = encodeURIComponent(runId);
  return fetchJson<RunHistorySnapshot>(
    `/api/runs/${encodedRunId}/history`,
    {},
    'run history request failed',
  );
}

export async function createRun(body: CreateRunRequest): Promise<RunRecord> {
  return fetchJson<RunRecord>(
    '/api/runs',
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    },
    'create run request failed',
  );
}

async function postRunAction(runId: string, action: string, errorLabel: string): Promise<RunRecord> {
  return fetchJson<RunRecord>(
    `/api/runs/${runId}/${action}`,
    { method: 'POST' },
    errorLabel,
  );
}

export function completeRun(runId: string): Promise<RunRecord> {
  return postRunAction(runId, 'complete', 'complete run request failed');
}

export function markRunReviewReady(runId: string): Promise<RunRecord> {
  return postRunAction(runId, 'review-ready', 'review-ready request failed');
}

export function stopRun(runId: string): Promise<RunRecord> {
  return postRunAction(runId, 'stop', 'stop run request failed');
}

export function resumeRun(runId: string): Promise<RunRecord> {
  return postRunAction(runId, 'resume', 'resume run request failed');
}

export function approveRun(runId: string): Promise<RunRecord> {
  return postRunAction(runId, 'approve', 'approve run request failed');
}

export function rejectRun(runId: string): Promise<RunRecord> {
  return postRunAction(runId, 'reject', 'reject run request failed');
}
