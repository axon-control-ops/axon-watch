import { describe, expect, it } from 'vitest';

import type { OperatorBriefing } from '../contracts/canonical';
import {
  briefingConnectivityLabels,
  briefingHasTopSignals,
  briefingIsEmpty,
  briefingPanelHeadline,
} from './briefing-panel-view';

const emptyBriefing: OperatorBriefing = {
  generated_at: '2026-07-04T08:00:00Z',
  top_signals: [],
  pending_approvals: { count: 0, items: [] },
  active_runs: [],
  next_safe_actions: [],
  degraded: { active: false, reasons: [] },
  connectivity: { control_plane_ready: true, watch_connected: true },
};

const approvalBriefing: OperatorBriefing = {
  ...emptyBriefing,
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
  it('reports nominal headline when no pending approvals exist', () => {
    expect(briefingPanelHeadline(emptyBriefing, 'loaded')).toBe('Systems nominal');
    expect(briefingIsEmpty(emptyBriefing)).toBe(true);
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
});
