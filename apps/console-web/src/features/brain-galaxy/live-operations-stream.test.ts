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
    expect(
      items.some(
        (item) =>
          item.text.includes('Last job failed') ||
          item.text.includes('closing Confidence line was missing'),
      ),
    ).toBe(true);
  });

  it('does not surface success-like stale failed tags as critical employee events', () => {
    const items = projectLiveOperationsStream({
      briefing: null,
      primaryActiveRun: null,
      employees: [
        {
          employee_id: 'employee-priya',
          name: 'Priya',
          role: 'frontend',
          status: 'idle',
          last_outcome: 'failed',
          last_outcome_detail: 'Run completed',
        },
      ] as never,
      presencePhase: 'idle',
    });
    expect(items.some((item) => item.id === 'emp-fail-employee-priya')).toBe(false);
  });

  it('collapses near-identical notice/advise lines', () => {
    const line = 'Lead-team plans are waiting for you in Mission Control — Seven of them.';
    const items = projectLiveOperationsStream({
      briefing: {
        notice: line,
        advise: line,
        top_signals: [],
      } as never,
      primaryActiveRun: null,
      employees: [],
      presencePhase: 'speaking',
    });
    const matches = items.filter((item) => item.text.includes('Lead-team plans'));
    expect(matches).toHaveLength(1);
  });

  it('collapses nested Lead-plan + DashPro advise/signal twins', () => {
    const short = 'Lead-team plans are waiting for you in Mission Control — Seven of them.';
    const items = projectLiveOperationsStream({
      briefing: {
        notice: short,
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
      employees: [],
      presencePhase: 'speaking',
    });
    expect(items.filter((item) => /Lead-team plans/i.test(item.text))).toHaveLength(1);
    expect(items.filter((item) => /DashPro Sentry critical/i.test(item.text))).toHaveLength(1);
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

  it('surfaces autonomous mode and critical attend receipts', () => {
    const items = projectLiveOperationsStream({
      briefing: null,
      primaryActiveRun: null,
      employees: [],
      presencePhase: 'autonomous',
      autonomyMode: 'full',
      autonomyReceipts: [
        {
          receipt_id: 'auton-1',
          kind: 'critical_signal',
          decision: 'escalate',
          title: 'Sentry critical needs approval',
          ask_operator: true,
          risk: 'critical',
        },
        {
          receipt_id: 'auton-2',
          kind: 'warning_signal',
          decision: 'dispatch',
          title: 'Fast Gate repair',
          ask_operator: false,
          risk: 'normal',
          created_at: '2026-07-29T18:04:05Z',
        },
        {
          receipt_id: 'auton-3',
          kind: 'critical_signal',
          decision: 'escalate',
          title: 'Resolved critical action',
          ask_operator: true,
          status: 'resolved',
          resolution: 'approved',
          risk: 'critical',
        },
      ],
    });
    expect(items.some((item) => item.kind === 'autonomy' && /AUTONOMOUS ON/i.test(item.text))).toBe(
      true,
    );
    expect(items.some((item) => /Needs you/i.test(item.text))).toBe(true);
    expect(items.some((item) => /Dispatched/i.test(item.text))).toBe(true);
    expect(items.some((item) => /Approved · Resolved critical action/i.test(item.text))).toBe(true);
    expect(items.some((item) => /Needs you · Resolved critical action/i.test(item.text))).toBe(false);
    expect(items.find((item) => item.id === 'auton-auton-2')?.tone).toBe('info');
    const dispatchTime = new Date('2026-07-29T18:04:05Z');
    const expectedTime = [
      String(dispatchTime.getHours()).padStart(2, '0'),
      String(dispatchTime.getMinutes()).padStart(2, '0'),
      String(dispatchTime.getSeconds()).padStart(2, '0'),
    ].join(':');
    expect(items.find((item) => item.id === 'auton-auton-2')?.at).toBe(expectedTime);
  });
});
