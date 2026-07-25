import { fetchBlob, fetchJson } from './client';

export interface OperatorDataSnapshotResponse {
  data: {
    updated_at: string;
    control_plane: {
      runs: { total: number; count: number; items: Record<string, unknown>[] };
      chat_threads: { total: number; count: number; items: Record<string, unknown>[] };
      chat_messages: { total: number; count: number; items: Record<string, unknown>[] };
      handoffs: { total: number; count: number; items: Record<string, unknown>[] };
    };
    watch: Record<string, { total: number; count: number; items: Record<string, unknown>[] }>;
  };
}

export async function fetchDataSnapshot(): Promise<OperatorDataSnapshotResponse> {
  return fetchJson<OperatorDataSnapshotResponse>(
    '/api/data/snapshot',
    {},
    'data snapshot request failed',
  );
}

export async function downloadDataExport(): Promise<Blob> {
  return fetchBlob('/api/data/export', {}, 'data export request failed');
}
