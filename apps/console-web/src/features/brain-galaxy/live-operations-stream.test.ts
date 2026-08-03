import { describe, expect, it } from 'vitest';

import { projectLiveOperationsStream } from './live-operations-stream';

describe('projectLiveOperationsStream', () => {
  it('surfaces current signals, not historical employee failures', () => {
    const items = projectLiveOperationsStream({
      briefing: {
        generated_at: new Date().toISOString(),
        notice: '4 Lead plans awaiting engagement in VAXON.',
        advise: 'Inspect DashPro Sentry critical.',
        top_signals: [
          {
            signal_id: 'signal_sentry',
            title: 'DashPro Sentry critical',
            severity: 'critical',
            status: 'open',
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
    expect(items.some((item) => item.agent === 'MARCO')).toBe(false);
    expect(items.some((item) => item.tone === 'critical')).toBe(true);
    expect(items.some((item) => item.text.includes('Last job failed'))).toBe(false);
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

  it('surfaces only current, unresolved autonomous work', () => {
    const now = new Date('2026-08-02T12:00:00Z');
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
          created_at: '2026-08-02T11:59:45Z',
        },
        {
          receipt_id: 'auton-2',
          kind: 'warning_signal',
          decision: 'dispatch',
          title: 'Fast Gate repair',
          ask_operator: false,
          risk: 'normal',
          created_at: '2026-08-02T11:59:30Z',
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
      now,
    });
    expect(items.some((item) => item.kind === 'autonomy' && /AUTONOMOUS ON/i.test(item.text))).toBe(
      true,
    );
    expect(items.some((item) => /Needs you/i.test(item.text))).toBe(true);
    expect(items.some((item) => /Dispatched/i.test(item.text))).toBe(true);
    expect(items.some((item) => /Resolved critical action/i.test(item.text))).toBe(false);
    expect(items.find((item) => item.id === 'auton-auton-2')?.tone).toBe('info');
    const dispatchTime = new Date('2026-08-02T11:59:30Z');
    const expectedTime = [
      String(dispatchTime.getHours()).padStart(2, '0'),
      String(dispatchTime.getMinutes()).padStart(2, '0'),
      String(dispatchTime.getSeconds()).padStart(2, '0'),
    ].join(':');
    expect(items.find((item) => item.id === 'auton-auton-2')?.at).toBe(expectedTime);
  });

  it('never replays terminal runs, receipts, signals, or routing diagnostics', () => {
    const items = projectLiveOperationsStream({
      briefing: {
        notice: 'Lead-team plans are ready for VAXON engagement in Mission Control — Two of them.',
        top_signals: [
          { signal_id: 'closed', title: 'Previously resolved', severity: 'critical', status: 'resolved' },
        ],
      } as never,
      primaryActiveRun: { run_id: 'run-old', phase: 'completed', summary: 'Old deployment' } as never,
      employees: [],
      presencePhase: 'idle',
      routingReceipt: 'old routing receipt',
      autonomyReceipts: [
        {
          receipt_id: 'old',
          title: 'Completed repair',
          status: 'completed',
          created_at: '2026-08-02T11:59:50Z',
        },
      ],
      now: new Date('2026-08-02T12:00:00Z'),
    });

    expect(items).toHaveLength(1);
    expect(items[0]?.id).toBe('standby');
  });

  it('suppresses briefing prose once its snapshot has expired', () => {
    const items = projectLiveOperationsStream({
      briefing: {
        generated_at: '2026-08-02T11:57:00Z',
        notice: 'Old CI issue',
        advise: 'Old CI advice',
        top_signals: [],
      } as never,
      primaryActiveRun: null,
      employees: [],
      presencePhase: 'idle',
      now: new Date('2026-08-02T12:00:00Z'),
    });

    expect(items).toHaveLength(1);
    expect(items[0]?.id).toBe('standby');
  });
});
