import type { OperatorBriefing, RunRecord, RuntimeSummary } from '../../contracts/canonical';
import type { RunHistoryRow } from '../run-history-view';
import { runPhaseTag } from '../mockup-shell-view';
import {
  formatRunDisplayName,
  formatRunIdentityLabel,
  formatRunShortId,
  humanizeRunSummary,
} from '../run-display';
import { isAutoCompleteRunSummary } from '../operator-run-strip-view';
import type {
  OperatorMissionStep,
  OperatorMissionSummary,
  OperatorRadarTone,
  OperatorStatusLoadState,
  OperatorStatusMetric,
  OperatorStatusMetricTone,
} from './types';
import { countHighPrioritySignals, elapsedLabel, truncatePanelCopy } from './helpers';

function requiredConnectorHeadline(count: number): string {
  if (count === 1) {
    return '1 required connector is down — restore the watch lane before more work.';
  }
  return `${count} required connectors are down — restore the watch lane before more work.`;
}

function requiredConnectorAdvise(count: number): string {
  const noun = count === 1 ? 'connector' : 'connectors';
  return `Open Mission Control → Connectors, reprobe the required ${noun}, then refresh summary.`;
}

export function operatorRadarTone(input: {
  runtimeSummary: RuntimeSummary | null;
  briefing: OperatorBriefing | null;
  pendingApprovals: number;
  requiredConnectorsUnavailable?: number;
}): OperatorRadarTone {
  if (input.briefing?.degraded.active || input.runtimeSummary?.degraded.active) {
    return 'degraded';
  }

  if (
    (input.requiredConnectorsUnavailable ?? 0) > 0 ||
    input.pendingApprovals > 0 ||
    countHighPrioritySignals(input.briefing) > 0
  ) {
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
  workspaceReviewReadyCount?: number;
  requiredConnectorsUnavailable?: number;
}): string {
  if (input.loadState === 'loading') {
    return 'Loading operator status…';
  }

  if (input.loadState === 'error') {
    return 'Runtime status unavailable';
  }

  const workspaceReviewReadyCount = input.workspaceReviewReadyCount ?? 0;
  if (workspaceReviewReadyCount > 0) {
    const autoCompleteBacklog =
      workspaceReviewReadyCount > 1 &&
      input.primaryActiveRun?.phase === 'review_ready' &&
      isAutoCompleteRunSummary(input.primaryActiveRun.summary);
    if (autoCompleteBacklog && input.primaryActiveRun) {
      const label = formatRunDisplayName(input.primaryActiveRun);
      return `${workspaceReviewReadyCount}× ${label} runs queued — use Complete all to clear.`;
    }
    if (workspaceReviewReadyCount === 1 && input.primaryActiveRun?.phase === 'review_ready') {
      return `${formatRunDisplayName(input.primaryActiveRun)} is ready for your review.`;
    }
    const noun = workspaceReviewReadyCount === 1 ? 'run is' : 'runs are';
    return `${workspaceReviewReadyCount} ${noun} ready for your review in this workspace.`;
  }

  const requiredConnectorsUnavailable = input.requiredConnectorsUnavailable ?? 0;
  if (!input.primaryActiveRun && requiredConnectorsUnavailable > 0) {
    return requiredConnectorHeadline(requiredConnectorsUnavailable);
  }

  if (input.briefing?.notice) {
    return input.briefing.notice;
  }

  if (input.primaryActiveRun?.phase === 'review_ready') {
    return `${formatRunDisplayName(input.primaryActiveRun)} is ready for your review.`;
  }

  if (input.primaryActiveRun) {
    return `${formatRunIdentityLabel(input.primaryActiveRun)} · ${runPhaseTag(input.primaryActiveRun.phase)}`;
  }

  return 'Systems nominal. No active run in this workspace.';
}

export function operatorStatusAdvise(input: {
  briefing: OperatorBriefing | null;
  loadState: OperatorStatusLoadState;
  primaryActiveRun?: RunRecord | null;
  requiredConnectorsUnavailable?: number;
}): string {
  if (input.loadState === 'loading') {
    return 'Standing by for briefing projection.';
  }

  if (input.loadState === 'error') {
    return 'Review connectivity before dispatching more work.';
  }

  const requiredConnectorsUnavailable = input.requiredConnectorsUnavailable ?? 0;
  if (!input.primaryActiveRun && requiredConnectorsUnavailable > 0) {
    return requiredConnectorAdvise(requiredConnectorsUnavailable);
  }

  return input.briefing?.advise ?? 'Describe the next action in Command.';
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

export function operatorMissionSummary(input: {
  workspaceId: string | null;
  runtimeSummary: RuntimeSummary | null;
  primaryActiveRun: RunRecord | null;
}): OperatorMissionSummary {
  const run = input.primaryActiveRun;
  const watchConnected = input.runtimeSummary?.watch.connected ?? false;
  if (!run) {
    return {
      runId: 'No active run',
      displayName: 'No active run',
      shortId: '—',
      identityLabel: 'No active run',
      phase: 'IDLE',
      workspace: input.workspaceId ?? 'none selected',
      status: 'standing by',
      elapsed: '—',
      currentStep: 'Waiting for the next command.',
      watchConnected,
    };
  }

  const displayName = formatRunDisplayName(run);
  return {
    runId: run.run_id,
    displayName,
    shortId: formatRunShortId(run.run_id),
    identityLabel: formatRunIdentityLabel(run),
    phase: runPhaseTag(run.phase),
    workspace: run.workspace_id,
    status: run.status,
    elapsed: elapsedLabel(run.started_at, run.ended_at, run.updated_at),
    currentStep: run.current_step ?? displayName,
    watchConnected,
  };
}

export function buildOperatorMissionSteps(input: {
  historyRows: RunHistoryRow[];
  currentStep: string | null;
  advise: string;
}): OperatorMissionStep[] {
  const steps: OperatorMissionStep[] = input.historyRows
    .slice(0, 3)
    .reverse()
    .map((row) => ({
      label: truncatePanelCopy(row.label, 84),
      tone: 'done' as const,
      meta: row.timestamp,
    }));

  if (input.currentStep) {
    steps.push({
      label: truncatePanelCopy(input.currentStep, 84),
      tone: 'active',
      meta: 'Current step',
    });
  }

  if (input.advise) {
    const activeLabel = input.currentStep?.trim() ?? '';
    if (input.advise.trim() !== activeLabel) {
      steps.push({
        label: truncatePanelCopy(input.advise, 84),
        tone: 'pending',
        meta: 'Next operator action',
      });
    }
  }

  if (steps.length === 0) {
    steps.push({
      label: 'Await operator input',
      tone: 'pending',
      meta: 'No active run history yet',
    });
  }

  return steps.slice(-5);
}
