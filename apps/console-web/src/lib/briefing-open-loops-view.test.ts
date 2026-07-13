import { describe, expect, it } from 'vitest';

import type { OperatorBriefing } from '../contracts/canonical';
import {
  briefingHasOpenLoops,
  buildBriefingOpenLoopRows,
} from './briefing-open-loops-view';

const baseBriefing: OperatorBriefing = {
  generated_at: '2026-07-13T10:00:00Z',
  notice: 'Standing by.',
  advise: 'Describe the next action.',
  executive_rhythm: {
    notice: 'Standing by.',
    advise: 'Describe the next action.',
    decide: '',
    execute: '',
    verify: '',
    report: '',
  },
  top_signals: [],
  pending_approvals: { count: 0, items: [] },
  active_runs: [],
  next_safe_actions: [],
  degraded: { active: false, reasons: [] },
  connectivity: { control_plane_ready: true, watch_connected: true },
};

describe('briefing-open-loops-view', () => {
  it('returns no rows when briefing is empty', () => {
    expect(buildBriefingOpenLoopRows(null)).toEqual([]);
    expect(briefingHasOpenLoops(baseBriefing)).toBe(false);
  });

  it('surfaces top signal with delivery badge and up to two safe actions', () => {
    const briefing: OperatorBriefing = {
      ...baseBriefing,
      top_signals: [
        {
          signal_id: 'sig_email_1',
          workspace_id: 'workspace_alpha',
          title: 'Urgent vendor reply',
          summary: 'Needs triage',
          severity: 'high',
          status: 'open',
          source: 'email',
          created_at: '2026-07-13T09:00:00Z',
          updated_at: '2026-07-13T09:00:00Z',
          action_type: 'investigate',
          delivery_state: 'delivered',
          latest_receipt_id: 'rcpt_1',
        },
      ],
      next_safe_actions: [
        {
          action_id: 'approve_run_a',
          kind: 'approve_run',
          title: 'Approve guarded run',
          detail: 'Approve run_a',
          workspace_id: 'workspace_alpha',
          run_id: 'run_a',
          signal_id: null,
        },
        {
          action_id: 'review_sig_email_1',
          kind: 'review_signal',
          title: 'Review top signal',
          detail: 'Inspect Urgent vendor reply.',
          workspace_id: 'workspace_alpha',
          run_id: null,
          signal_id: 'sig_email_1',
        },
        {
          action_id: 'inspect_runtime_degraded',
          kind: 'inspect_runtime',
          title: 'Inspect degraded runtime',
          detail: 'Check connectivity.',
          workspace_id: null,
          run_id: null,
          signal_id: null,
        },
      ],
    };

    const rows = buildBriefingOpenLoopRows(briefing);
    expect(rows).toHaveLength(3);
    expect(rows[0]).toMatchObject({
      label: 'Urgent vendor reply',
      meta: 'Receipt rcpt_1',
      focusKind: 'attention',
      signalId: 'sig_email_1',
    });
    expect(rows[1]).toMatchObject({
      label: 'Approve guarded run',
      focusKind: 'mission',
    });
    expect(rows[2]).toMatchObject({
      label: 'Review top signal',
      focusKind: 'attention',
      signalId: 'sig_email_1',
    });
    expect(briefingHasOpenLoops(briefing)).toBe(true);
  });

  it('routes inspect_runtime actions to command focus', () => {
    const briefing: OperatorBriefing = {
      ...baseBriefing,
      next_safe_actions: [
        {
          action_id: 'inspect_runtime_degraded',
          kind: 'inspect_runtime',
          title: 'Inspect degraded runtime',
          detail: 'Check connectivity.',
          workspace_id: null,
          run_id: null,
          signal_id: null,
        },
      ],
    };
    expect(buildBriefingOpenLoopRows(briefing)[0]).toMatchObject({
      focusKind: 'command',
      label: 'Inspect degraded runtime',
    });
  });

  it('surfaces pending approvals when no top signal', () => {
    const briefing: OperatorBriefing = {
      ...baseBriefing,
      pending_approvals: {
        count: 2,
        items: [{ approval_id: 'appr_1', run_id: 'run_a', workspace_id: 'workspace_alpha' }],
      },
    };
    expect(buildBriefingOpenLoopRows(briefing)[0]).toMatchObject({
      label: '2 approvals waiting',
      meta: 'Run run_a',
      focusKind: 'mission',
    });
  });

  it('compacts to two rows for galaxy hero', () => {
    const briefing: OperatorBriefing = {
      ...baseBriefing,
      top_signals: [
        {
          signal_id: 'sig_1',
          workspace_id: 'workspace_alpha',
          title: 'Signal one',
          summary: 'Summary',
          severity: 'warning',
          status: 'open',
          source: 'watch',
          created_at: '2026-07-13T09:00:00Z',
          updated_at: '2026-07-13T09:00:00Z',
          action_type: 'investigate',
        },
      ],
      next_safe_actions: [
        {
          action_id: 'a1',
          kind: 'approve_run',
          title: 'Action 1',
          detail: 'd1',
          workspace_id: null,
          run_id: 'r1',
          signal_id: null,
        },
        {
          action_id: 'a2',
          kind: 'resume_run',
          title: 'Action 2',
          detail: 'd2',
          workspace_id: null,
          run_id: 'r2',
          signal_id: null,
        },
      ],
    };
    expect(buildBriefingOpenLoopRows(briefing, { compact: true })).toHaveLength(2);
  });

  it('caps at four rows', () => {
    const briefing: OperatorBriefing = {
      ...baseBriefing,
      top_signals: [
        {
          signal_id: 'sig_1',
          workspace_id: 'workspace_alpha',
          title: 'Signal one',
          summary: 'Summary',
          severity: 'warning',
          status: 'open',
          source: 'watch',
          created_at: '2026-07-13T09:00:00Z',
          updated_at: '2026-07-13T09:00:00Z',
          action_type: 'investigate',
        },
      ],
      next_safe_actions: [
        {
          action_id: 'a1',
          kind: 'approve_run',
          title: 'Action 1',
          detail: 'd1',
          workspace_id: null,
          run_id: 'r1',
          signal_id: null,
        },
        {
          action_id: 'a2',
          kind: 'resume_run',
          title: 'Action 2',
          detail: 'd2',
          workspace_id: null,
          run_id: 'r2',
          signal_id: null,
        },
      ],
    };

    expect(buildBriefingOpenLoopRows(briefing).length).toBeLessThanOrEqual(4);
  });

  it('surfaces the primary active run when there are no signals', () => {
    const rows = buildBriefingOpenLoopRows(baseBriefing, {
      primaryActiveRun: {
        run_id: 'run_review_me',
        summary: 'Review me',
        detail: 'Lane B agent-mode runtime request',
        phase: 'review_ready',
        workspace_id: 'workspace_dashpro',
      },
      workspaceId: 'workspace_dashpro',
    });
    expect(rows[0]).toMatchObject({
      id: 'run:run_review_me',
      label: 'Review me',
      meta: 'REVIEW READY',
      focusKind: 'mission',
    });
    expect(briefingHasOpenLoops(baseBriefing, {
      primaryActiveRun: {
        run_id: 'run_review_me',
        summary: 'Review me',
        detail: '',
        phase: 'executing',
        workspace_id: 'workspace_dashpro',
      },
    })).toBe(true);
  });

  it('surfaces fleet runs when this workspace is idle', () => {
    const rows = buildBriefingOpenLoopRows(baseBriefing, {
      primaryActiveRun: null,
      workspaceId: 'workspace_dashpro',
      fleetActiveRuns: [
        {
          run_id: 'run_elsewhere',
          workspace_id: 'workspace_axon_local',
          phase: 'executing',
          title: 'Elsewhere',
          mode: 'agent',
          status: 'running',
          detail: '',
          lane_id: 'control-plane',
          updated_at: '2026-07-13T10:00:00Z',
        },
      ],
    });
    expect(rows[0]).toMatchObject({
      label: '1 run in flight (other workspaces)',
      meta: 'Open Brain view',
      focusKind: 'mission',
    });
  });

  it('keeps compact galaxy hero at two rows including a live run', () => {
    const briefing: OperatorBriefing = {
      ...baseBriefing,
      next_safe_actions: [
        {
          action_id: 'a1',
          kind: 'approve_run',
          title: 'Action 1',
          detail: 'd1',
          workspace_id: null,
          run_id: 'r1',
          signal_id: null,
        },
        {
          action_id: 'a2',
          kind: 'resume_run',
          title: 'Action 2',
          detail: 'd2',
          workspace_id: null,
          run_id: 'r2',
          signal_id: null,
        },
      ],
    };
    expect(
      buildBriefingOpenLoopRows(briefing, {
        compact: true,
        primaryActiveRun: {
          run_id: 'run_live',
          summary: 'Live task',
          detail: '',
          phase: 'executing',
          workspace_id: 'workspace_dashpro',
        },
      }),
    ).toHaveLength(2);
  });
});
