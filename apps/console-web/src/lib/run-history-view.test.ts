import { describe, expect, it } from 'vitest';

import { buildRunHistoryRows, type RunHistorySnapshot } from './run-history-view';

describe('run-history-view', () => {
  it('builds newest-first receipt rows with summaries', () => {
    const snapshot: RunHistorySnapshot = {
      run_id: 'run_test',
      history_ref: 'history/run_test',
      count: 3,
      items: [
        {
          from_phase: null,
          to_phase: 'queued',
          timestamp: '2026-07-04T10:00:00Z',
          actor: 'control-plane',
          receipt: { type: 'run_created', summary: 'Run created' },
        },
        {
          from_phase: 'executing',
          to_phase: 'review_ready',
          timestamp: '2026-07-04T10:01:00Z',
          actor: 'control-plane',
          receipt: {
            type: 'review_ready',
            summary: 'Active execution stopped; run awaiting operator review',
          },
        },
        {
          from_phase: 'review_ready',
          to_phase: 'executing',
          timestamp: '2026-07-04T10:02:00Z',
          actor: 'operator',
          receipt: {
            type: 'operator_resume',
            summary: 'Operator resumed the run from review_ready',
          },
        },
      ],
    };

    const rows = buildRunHistoryRows(snapshot, 2);
    expect(rows).toHaveLength(2);
    expect(rows[0]?.label).toContain('Operator resumed');
    expect(rows[1]?.label).toContain('awaiting operator review');
  });

  it('returns empty rows when history is missing', () => {
    expect(buildRunHistoryRows(null)).toEqual([]);
  });
});
