import { describe, expect, it, vi } from 'vitest';

import type { OperatorBriefing } from '../contracts/canonical';

import {
  briefingActionCtaLabel,
  executeBriefingAction,
  findBriefingSignal,
} from './briefing-action-executor';

function baseBriefing(overrides: Partial<OperatorBriefing> = {}): OperatorBriefing {
  return {
    generated_at: '2026-07-17T00:00:00Z',
    notice: '',
    advise: '',
    executive_rhythm: {
      notice: '',
      advise: '',
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
    ...overrides,
  };
}

function createShell() {
  return {
    handoffSignalToIde: vi.fn().mockResolvedValue(undefined),
    focusMissionControl: vi.fn(),
    focusCommandSeam: vi.fn(),
    focusAttentionSidebar: vi.fn(),
  };
}

describe('briefing-action-executor', () => {
  it('finds a briefing signal by id', () => {
    const briefing = baseBriefing({
      top_signals: [
        {
          signal_id: 'sig_ci_1',
          workspace_id: 'workspace_axon_watch',
          title: 'Run failed: Axon-X Fast Gate',
          summary: 'CI failed on main.',
          severity: 'critical',
          status: 'open',
          source: 'watch',
          created_at: '2026-07-17T00:00:00Z',
          updated_at: '2026-07-17T00:00:00Z',
          action_type: 'notify',
        },
      ],
    });

    expect(findBriefingSignal(briefing, 'sig_ci_1')?.title).toBe('Run failed: Axon-X Fast Gate');
    expect(findBriefingSignal(briefing, 'missing')).toBeNull();
  });

  it('routes approve_run to mission control', async () => {
    const shell = createShell();
    const action = {
      action_id: 'approve_run_a',
      kind: 'approve_run' as const,
      title: 'Approve guarded run',
      detail: 'Approve run_a',
      workspace_id: 'workspace_alpha',
      run_id: 'run_a',
      signal_id: null,
    };

    const result = await executeBriefingAction(shell, null, action);

    expect(result).toEqual({ ok: true, kind: 'approve_run' });
    expect(shell.focusMissionControl).toHaveBeenCalledTimes(1);
    expect(shell.handoffSignalToIde).not.toHaveBeenCalled();
  });

  it('routes inspect_runtime to command seam', async () => {
    const shell = createShell();
    const action = {
      action_id: 'inspect_runtime',
      kind: 'inspect_runtime' as const,
      title: 'Inspect degraded runtime',
      detail: 'Check connectivity.',
      workspace_id: null,
      run_id: null,
      signal_id: null,
    };

    const result = await executeBriefingAction(shell, null, action);

    expect(result).toEqual({ ok: true, kind: 'inspect_runtime' });
    expect(shell.focusCommandSeam).toHaveBeenCalledTimes(1);
  });

  it('hands off review_signal without auto-submit', async () => {
    const shell = createShell();
    const briefing = baseBriefing({
      top_signals: [
        {
          signal_id: 'sig_ci_1',
          workspace_id: 'workspace_axon_watch',
          title: 'Run failed: Axon-X Fast Gate',
          summary: 'CI failed on main.',
          severity: 'critical',
          status: 'open',
          source: 'watch',
          created_at: '2026-07-17T00:00:00Z',
          updated_at: '2026-07-17T00:00:00Z',
          action_type: 'notify',
        },
      ],
    });
    const action = {
      action_id: 'review_sig_ci_1',
      kind: 'review_signal' as const,
      title: 'Review top signal',
      detail: 'Inspect Run failed: Axon-X Fast Gate.',
      workspace_id: 'workspace_axon_watch',
      run_id: null,
      signal_id: 'sig_ci_1',
    };

    const result = await executeBriefingAction(shell, briefing, action);

    expect(result).toEqual({ ok: true, kind: 'review_signal' });
    expect(shell.handoffSignalToIde).toHaveBeenCalledWith(
      {
        signal_id: 'sig_ci_1',
        workspace_id: 'workspace_axon_watch',
        title: 'Run failed: Axon-X Fast Gate',
        summary: 'CI failed on main.',
        meta: null,
      },
      { autoSubmit: false },
    );
  });

  it('falls back to attention focus when signal cannot hand off', async () => {
    const shell = createShell();
    const action = {
      action_id: 'review_bootstrap',
      kind: 'review_signal' as const,
      title: 'Review top signal',
      detail: 'Inspect bootstrap summary.',
      workspace_id: 'workspace_alpha',
      run_id: null,
      signal_id: 'signal_watch_bootstrap_ready',
    };

    const result = await executeBriefingAction(shell, null, action);

    expect(result).toEqual({ ok: true, kind: 'review_signal' });
    expect(shell.focusAttentionSidebar).toHaveBeenCalledWith('signal_watch_bootstrap_ready');
    expect(shell.handoffSignalToIde).not.toHaveBeenCalled();
  });

  it('labels review_signal as IDE handoff', () => {
    expect(
      briefingActionCtaLabel({
        action_id: 'review_sig',
        kind: 'review_signal',
        title: 'Review top signal',
        detail: 'Inspect signal.',
        workspace_id: null,
        run_id: null,
        signal_id: 'sig_1',
      }),
    ).toBe('Hand off to IDE');
  });
});
