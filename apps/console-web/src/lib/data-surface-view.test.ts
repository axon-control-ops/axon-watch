import { describe, expect, it } from 'vitest';

import { buildDataSurfaceTables } from './data-surface-view';

describe('buildDataSurfaceTables', () => {
  it('maps control-plane and watch tables for the data surface', () => {
    const tables = buildDataSurfaceTables({
      updated_at: '2026-07-06T05:00:00Z',
      control_plane: {
        runs: { total: 1, count: 1, items: [{ run_id: 'run-1', status: 'running' }] },
        chat_threads: { total: 0, count: 0, items: [] },
        chat_messages: { total: 0, count: 0, items: [] },
        handoffs: { total: 0, count: 0, items: [] },
      },
      watch: {
        commands: { total: 0, count: 0, items: [] },
        events: { total: 0, count: 0, items: [] },
        receipts: { total: 0, count: 0, items: [] },
        suppressions: { total: 0, count: 0, items: [] },
      },
    });

    expect(tables).toHaveLength(8);
    expect(tables[0]?.id).toBe('runs');
    expect(tables[0]?.total).toBe(1);
  });
});
