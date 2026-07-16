import { describe, expect, it } from 'vitest';

import type { ExecutiveOperatorRhythm, OperatorBriefing } from '../contracts/canonical';
import {
  briefingAdvise,
  briefingConnectivityLabels,
  briefingHasTopSignals,
  briefingIsEmpty,
  briefingNotice,
  briefingPanelHeadline,
  briefingRhythmField,
} from './briefing-panel-view';

function rhythmFrom(
  notice: string,
  advise: string,
  overrides: Partial<ExecutiveOperatorRhythm> = {},
): ExecutiveOperatorRhythm {
  return {
    notice,
    advise,
    decide: 'Decide whether to continue.',
    execute: 'Execute the next safe action.',
    verify: 'Verify canonical state before continuing.',
    report: 'Report: systems nominal.',
    ...overrides,
  };
}

const emptyBriefing: OperatorBriefing = {
  generated_at: '2026-07-04T08:00:00Z',
  notice: 'No active runs. Systems nominal.',
  advise: 'Describe the next action in Command.',
  executive_rhythm: rhythmFrom(
    'No active runs. Systems nominal.',
    'Describe the next action in Command.',
  ),
  top_signals: [],
  pending_approvals: { count: 0, items: [] },
  active_runs: [],
  next_safe_actions: [],
  degraded: { active: false, reasons: [] },
  connectivity: { control_plane_ready: true, watch_connected: true },
};

const approvalBriefing: OperatorBriefing = {
  ...emptyBriefing,
  notice: '1 run awaiting explicit approval.',
  advise: 'Approve test run to continue execution.',
  executive_rhythm: rhythmFrom(
    '1 run awaiting explicit approval.',
    'Approve test run to continue execution.',
    {
      decide: 'Decide whether to approve or reject the guarded run before execution continues.',
      execute: 'Execute: approve the guarded run to unblock execution.',
    },
  ),
  pending_approvals: {
    count: 1,
    items: [
      {
        approval_id: 'approval_run_test',
        run_id: 'run_test',
        workspace_id: 'workspace_alpha',
      },
    ],
  },
  next_safe_actions: [
    {
      action_id: 'approve_run_test',
      kind: 'approve_run',
      title: 'Approve guarded run',
      detail: 'Approve test run to continue execution.',
      workspace_id: 'workspace_alpha',
      run_id: 'run_test',
      signal_id: null,
    },
  ],
};

const signalBriefing: OperatorBriefing = {
  ...emptyBriefing,
  top_signals: [
    {
      signal_id: 'signal_bootstrap',
      workspace_id: 'workspace_alpha',
      title: 'Bootstrap degraded',
      summary: 'Watch summary degraded.',
      severity: 'warning',
      status: 'open',
      source: 'watch',
      created_at: '2026-07-03T16:00:00Z',
      updated_at: '2026-07-03T16:00:00Z',
      action_type: 'open_dashboard',
    },
  ],
};

describe('briefing panel view helpers', () => {
  it('keeps a compact idle headline without manufacturing briefing copy', () => {
    expect(briefingPanelHeadline(emptyBriefing, 'loaded')).toBe('Systems nominal');
    expect(briefingIsEmpty(emptyBriefing)).toBe(true);
    expect(briefingNotice(emptyBriefing, 'loaded')).toBe('');
    expect(briefingAdvise(emptyBriefing, 'loaded')).toBe('');
  });

  it('surfaces pending approval count from OperatorBriefing', () => {
    expect(briefingPanelHeadline(approvalBriefing, 'loaded')).toBe('1 pending approval(s)');
    expect(briefingIsEmpty(approvalBriefing)).toBe(false);
  });

  it('surfaces top signal title when no approvals are pending', () => {
    expect(briefingPanelHeadline(signalBriefing, 'loaded')).toBe('Bootstrap degraded');
    expect(briefingHasTopSignals(signalBriefing)).toBe(true);
    expect(briefingIsEmpty(signalBriefing)).toBe(false);
  });

  it('labels connectivity state for the briefing panel', () => {
    expect(
      briefingConnectivityLabels({
        control_plane_ready: true,
        watch_connected: false,
      }),
    ).toEqual(['Control plane ready', 'Watch disconnected']);
  });

  it('surfaces live notice and advice but suppresses generic idle filler', () => {
    expect(briefingNotice(approvalBriefing, 'loaded')).toBe(
      approvalBriefing.notice ?? '1 run awaiting explicit approval.',
    );
    expect(briefingAdvise(approvalBriefing, 'loaded')).toBe(
      'Approve test run to continue execution.',
    );
    expect(briefingNotice(signalBriefing, 'loaded')).toBe('Watch summary degraded.');
    expect(briefingAdvise(signalBriefing, 'loaded')).toBe('');
    expect(briefingRhythmField(approvalBriefing, 'decide', 'loaded')).toContain('approve or reject');
  });

  it('overrides idle no-runs notice when a primary active run exists', () => {
    expect(
      briefingNotice(emptyBriefing, 'loaded', {
        primaryActiveRun: {
          run_id: 'run_review_me',
          summary: 'Review me',
          detail: '',
          phase: 'review_ready',
        },
      }),
    ).toBe('Review me is ready for your review.');

    expect(
      briefingNotice(emptyBriefing, 'loaded', {
        primaryActiveRun: {
          run_id: 'run_abcdef123',
          summary: 'Build fix',
          detail: '',
          phase: 'executing',
        },
      }),
    ).toContain('EXECUTE');
  });
});
