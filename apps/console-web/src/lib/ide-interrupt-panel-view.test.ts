import { describe, expect, it } from 'vitest';

import {
  isIdeInterruptStopDisabled,
  resolveIdeInterruptDetailLine,
  resolveIdeInterruptHeadline,
  resolveIdeInterruptStopTarget,
  shouldShowIdeInterruptAttentionAction,
  shouldShowIdeInterruptStop,
} from './ide-interrupt-panel-view';

describe('ide interrupt panel view', () => {
  it('prioritizes watch connectivity over bootstrap info signals in the headline', () => {
    expect(
      resolveIdeInterruptHeadline({
        pendingApprovalsCount: 0,
        topSignal: {
          signal_id: 'signal_watch_bootstrap_ready',
          title: 'Watch bootstrap ready',
          severity: 'info',
        },
        watchConnected: false,
        degradedActive: true,
        primaryRunPhase: 'review_ready',
      }),
    ).toBe('Watch connector offline');
  });

  it('uses actionable signal titles when runtime is healthy', () => {
    expect(
      resolveIdeInterruptHeadline({
        pendingApprovalsCount: 0,
        topSignal: {
          signal_id: 'signal_monitor_dashpro',
          title: 'DashPro monitor warning',
          severity: 'high',
        },
        watchConnected: true,
        degradedActive: false,
        primaryRunPhase: null,
      }),
    ).toBe('DashPro monitor warning');
  });

  it('does not surface Open Attention for bootstrap-only inbox when healthy', () => {
    expect(
      shouldShowIdeInterruptAttentionAction({
        pendingApprovalsCount: 0,
        topSignals: [
          {
            signal_id: 'signal_watch_bootstrap_ready',
            title: 'Watch bootstrap ready',
            severity: 'info',
          },
        ],
        degradedActive: false,
      }),
    ).toBe(false);
  });

  it('surfaces degraded detail copy when watch probe failed', () => {
    expect(
      resolveIdeInterruptDetailLine({
        pendingApprovalsCount: 0,
        topSignal: {
          signal_id: 'signal_watch_bootstrap_ready',
          title: 'Watch bootstrap ready',
          severity: 'info',
        },
        watchConnected: false,
        degradedActive: true,
        primaryRunCurrentStep: null,
      }),
    ).toContain('check-health.sh');
  });

  it('prefers IDE agent stop when the composer stream is active', () => {
    expect(
      shouldShowIdeInterruptStop({
        canStopIdeAgentRun: true,
        canStopPrimaryRun: false,
        primaryRunPhase: 'executing',
        agentStreamActive: true,
      }),
    ).toBe(true);

    expect(
      resolveIdeInterruptStopTarget({
        canStopIdeAgentRun: true,
        agentStreamActive: true,
      }),
    ).toBe('ide-agent');
  });

  it('falls back to primary run stop when no IDE agent run is active', () => {
    expect(
      resolveIdeInterruptStopTarget({
        canStopIdeAgentRun: false,
        agentStreamActive: false,
      }),
    ).toBe('primary');
  });

  it('disables stop while mutation is in flight unless IDE agent stop is available', () => {
    expect(
      isIdeInterruptStopDisabled({
        runMutationStopping: true,
        canStopIdeAgentRun: false,
        canStopPrimaryRun: true,
        primaryRunPhase: 'executing',
      }),
    ).toBe(true);

    expect(
      isIdeInterruptStopDisabled({
        runMutationStopping: true,
        canStopIdeAgentRun: true,
        canStopPrimaryRun: false,
        primaryRunPhase: 'executing',
      }),
    ).toBe(true);
  });
});
