import { describe, expect, it } from 'vitest';

import { projectLiveOperationsStream } from './live-operations-stream';

describe('projectLiveOperationsStream', () => {
  it('surfaces advise, critical signals, and failed employee shifts', () => {
    const items = projectLiveOperationsStream({
      briefing: {
        notice: '4 Lead plans awaiting engagement in VAXON.',
        advise: 'Inspect DashPro Sentry critical.',
        top_signals: [
          {
            signal_id: 'signal_sentry',
            title: 'DashPro Sentry critical',
            severity: 'critical',
          },
        ],
      } as never,
      primaryActiveRun: null,
      employees: [
        {
          employee_id: 'employee-marco',
          name: 'Marco',
          role: 'backend',
          status: 'idle',
          last_outcome: 'failed',
          last_outcome_detail: 'Critical Review Clause missing',
        },
      ] as never,
      presencePhase: 'alerting',
      degradedReasons: ['CLI runtime not ready'],
    });

    expect(items.some((item) => item.text.includes('Sentry'))).toBe(true);
    expect(items.some((item) => item.agent === 'MARCO')).toBe(true);
    expect(items.some((item) => item.tone === 'critical')).toBe(true);
  });

  it('falls back to standby when there is nothing live', () => {
    const items = projectLiveOperationsStream({
      briefing: null,
      primaryActiveRun: null,
      employees: [],
      presencePhase: 'idle',
    });
    expect(items).toHaveLength(1);
    expect(items[0]?.text).toMatch(/standby/i);
  });
});
