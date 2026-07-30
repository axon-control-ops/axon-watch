import { describe, expect, it } from 'vitest';

import {
  isIdeInterruptStopDisabled,
  resolveIdeInterruptCompactLabel,
  resolveIdeInterruptDetailLine,
  resolveIdeInterruptHeadline,
  resolveIdeInterruptStopTarget,
  resolveIdeInterruptTooltip,
  shouldShowIdeInterruptAttentionAction,
  shouldShowIdeInterruptStop,
  truncateInterruptLabel,
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
        primaryRunPhase: 'review_ready',
      }),
    ).toBe('DashPro monitor warning');
  });

  it('labels remote-ingress-only issues without calling the local stack dead', () => {
    expect(
      resolveIdeInterruptHeadline({
        pendingApprovalsCount: 0,
        topSignal: null,
        watchConnected: true,
        degradedActive: false,
        remoteIngressAttention: true,
        primaryRunPhase: null,
      }),
    ).toBe('Remote ingress unhealthy — local Axon-X is up');
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

  it('builds compact and tooltip labels for long Sentry summaries', () => {
    const headline = 'DashPro Sentry critical';
    const detail =
      "Sentry returned 5 unresolved issue(s), 330 event(s); latest=Error: cannot add 'postgres_changes' callbacks";

    expect(resolveIdeInterruptCompactLabel(headline, detail).length).toBeLessThanOrEqual(72);
    expect(resolveIdeInterruptCompactLabel(headline, detail)).toContain('DashPro Sentry critical');
    expect(resolveIdeInterruptTooltip(headline, detail)).toContain('\n');
    expect(truncateInterruptLabel('short')).toBe('short');
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
