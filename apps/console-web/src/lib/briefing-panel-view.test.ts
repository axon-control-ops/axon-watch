import { describe, expect, it } from 'vitest';

import type { OperatorBriefing } from '../contracts/canonical';
import {
  briefingHasActions,
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

describe('briefing panel view helpers', () => {
  it('reports empty headline when no pending approvals exist', () => {
    expect(briefingPanelHeadline(emptyBriefing, 'loaded')).toBe('No pending approvals');
    expect(briefingIsEmpty(emptyBriefing)).toBe(true);
    expect(briefingHasActions(emptyBriefing)).toBe(false);
  });

  it('surfaces pending approval count from OperatorBriefing', () => {
    expect(briefingPanelHeadline(approvalBriefing, 'loaded')).toBe('1 pending approval(s)');
    expect(briefingIsEmpty(approvalBriefing)).toBe(false);
    expect(briefingHasActions(approvalBriefing)).toBe(true);
  });
});
