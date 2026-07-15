import { describe, expect, it } from 'vitest';

import { projectGalaxyIntelligence } from './galaxy-intelligence-projector';

describe('projectGalaxyIntelligence', () => {
  it('projects idle briefing defaults', () => {
    const view = projectGalaxyIntelligence({
      briefing: null,
      briefingLoadState: 'idle',
      primaryActiveRun: null,
      presencePhase: 'idle',
      workspaceLabel: null,
    });
    expect(view.headline).toBe('Awaiting briefing');
    expect(view.notice).toContain('Awaiting');
    expect(view.approvalCount).toBe(0);
  });

  it('surfaces approvals and run phase', () => {
    const view = projectGalaxyIntelligence({
      briefing: {
        generated_at: '2026-01-01T00:00:00Z',
        notice: 'Approvals waiting.',
        advise: 'Review pending runs.',
        executive_rhythm: {
          notice: '',
          advise: '',
          decide: '',
          execute: '',
          verify: '',
          report: '',
        },
        top_signals: [
          {
            signal_id: 's1',
            workspace_id: 'ws',
            title: 'Critical outage',
            summary: '',
            severity: 'critical',
            status: 'open',
            created_at: '',
            updated_at: '',
            source: 'watch',
            kind: 'runtime',
          } as never,
        ],
        pending_approvals: { count: 2, items: [] },
        active_runs: [],
        next_safe_actions: [
          {
            action_id: 'a1',
            kind: 'approve_run',
            title: 'Approve resume',
            detail: '',
            workspace_id: 'ws',
            run_id: 'r1',
            signal_id: null,
          },
        ],
        degraded: { active: false, reasons: [] },
        connectivity: {
          control_plane_ready: true,
          watch_connected: true,
        },
      },
      briefingLoadState: 'loaded',
      primaryActiveRun: {
        run_id: 'r1',
        summary: 'Health probe',
        detail: '',
        phase: 'awaiting_approval',
      },
      presencePhase: 'alerting',
      workspaceLabel: 'Axon Watch',
      routingReceipt: 'lane=template_status model=none',
    });

    expect(view.approvalCount).toBe(2);
    expect(view.criticalSignals).toBe(1);
    expect(view.safeActions).toHaveLength(1);
    expect(view.workspaceLabel).toBe('Axon Watch');
    expect(view.routingReceipt).toContain('template_status');
    expect(view.runPhaseLabel).toBeTruthy();
  });
});
