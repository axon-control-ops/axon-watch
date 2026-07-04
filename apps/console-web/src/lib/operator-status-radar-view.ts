import type { OperatorBriefing, RunRecord, RuntimeSummary } from '../contracts/canonical';

import { runPhaseTag } from './mockup-shell-view';

export type OperatorRadarTone = 'nominal' | 'watch' | 'attention' | 'degraded';
export type OperatorStatusMetricTone = 'default' | 'ok' | 'warn' | 'attention';

export interface OperatorStatusMetric {
  label: string;
  value: string;
  tone: OperatorStatusMetricTone;
}

export type OperatorStatusLoadState = 'idle' | 'loading' | 'loaded' | 'error';

function countHighPrioritySignals(briefing: OperatorBriefing | null): number {
  return (
    briefing?.top_signals.filter(
      (signal) => signal.severity === 'high' || signal.severity === 'critical',
    ).length ?? 0
  );
}

export function operatorRadarTone(input: {
  runtimeSummary: RuntimeSummary | null;
  briefing: OperatorBriefing | null;
  pendingApprovals: number;
}): OperatorRadarTone {
  if (input.briefing?.degraded.active || input.runtimeSummary?.degraded.active) {
    return 'degraded';
  }

  if (input.pendingApprovals > 0 || countHighPrioritySignals(input.briefing) > 0) {
    return 'attention';
  }

  const watchConnected =
    input.briefing?.connectivity.watch_connected ?? input.runtimeSummary?.watch.connected ?? false;
  if (!watchConnected) {
    return 'watch';
  }

  return 'nominal';
}

export function operatorStatusHeadline(input: {
  briefing: OperatorBriefing | null;
  loadState: OperatorStatusLoadState;
  primaryActiveRun: RunRecord | null;
}): string {
  if (input.loadState === 'loading') {
    return 'Loading operator status…';
  }

  if (input.loadState === 'error') {
    return 'Runtime status unavailable';
  }

  if (input.briefing?.notice) {
    return input.briefing.notice;
  }

  if (input.primaryActiveRun?.phase === 'review_ready') {
    return `${input.primaryActiveRun.summary} is ready for operator review.`;
  }

  if (input.primaryActiveRun) {
    return `Active run ${input.primaryActiveRun.run_id} · ${runPhaseTag(input.primaryActiveRun.phase)}`;
  }

  return 'Systems nominal. No active run in this workspace.';
}

export function operatorStatusAdvise(input: {
  briefing: OperatorBriefing | null;
  loadState: OperatorStatusLoadState;
}): string {
  if (input.loadState === 'loading') {
    return 'Standing by for briefing projection.';
  }

  if (input.loadState === 'error') {
    return 'Review connectivity before dispatching more work.';
  }

  return input.briefing?.advise ?? 'Describe the next operator action in Command.';
}

export function operatorStatusMetrics(input: {
  workspaceId: string | null;
  runtimeSummary: RuntimeSummary | null;
  runtimeSummaryLoadState: OperatorStatusLoadState;
  briefing: OperatorBriefing | null;
  briefingLoadState: OperatorStatusLoadState;
  primaryActiveRun: RunRecord | null;
  pendingApprovals: number;
}): OperatorStatusMetric[] {
  if (input.runtimeSummaryLoadState === 'loading' || input.briefingLoadState === 'loading') {
    return [
      { label: 'Workspace', value: input.workspaceId ?? '—', tone: 'default' },
      { label: 'Run phase', value: 'loading…', tone: 'default' },
      { label: 'Watch', value: 'loading…', tone: 'default' },
      { label: 'Signals', value: '…', tone: 'default' },
      { label: 'Approvals', value: '…', tone: 'default' },
      { label: 'Control plane', value: 'loading…', tone: 'default' },
    ];
  }

  const summary = input.runtimeSummary;
  const briefing = input.briefing;
  const watchConnected = briefing?.connectivity.watch_connected ?? summary?.watch.connected ?? false;
  const controlPlaneReady =
    briefing?.connectivity.control_plane_ready ?? summary?.control_plane.ready ?? false;
  const openSignals = briefing?.top_signals.length ?? summary?.signals.open_count ?? 0;
  const phase = input.primaryActiveRun?.phase ?? 'idle';
  const runStatus = input.primaryActiveRun?.status ?? 'none';

  return [
    {
      label: 'Workspace',
      value: input.workspaceId ?? 'none selected',
      tone: input.workspaceId ? 'ok' : 'warn',
    },
    {
      label: 'Run phase',
      value: input.primaryActiveRun ? `${runPhaseTag(phase)} · ${runStatus}` : 'IDLE',
      tone: input.primaryActiveRun?.phase === 'review_ready' ? 'attention' : 'default',
    },
    {
      label: 'Watch',
      value: watchConnected ? 'connected' : 'disconnected',
      tone: watchConnected ? 'ok' : 'warn',
    },
    {
      label: 'Signals',
      value: String(openSignals),
      tone: openSignals > 0 ? 'attention' : 'default',
    },
    {
      label: 'Approvals',
      value: String(input.pendingApprovals),
      tone: input.pendingApprovals > 0 ? 'attention' : 'default',
    },
    {
      label: 'Control plane',
      value: controlPlaneReady ? 'ready' : 'not ready',
      tone: controlPlaneReady ? 'ok' : 'warn',
    },
  ];
}
