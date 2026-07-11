import type { OperatorBriefing, RunRecord, RuntimeSummary } from '../contracts/canonical';
import type { RunHistoryRow } from './run-history-view';

import { runPhaseProgress, runPhaseTag } from './mockup-shell-view';
import { formatRunDisplayName, formatRunIdentityLabel, formatRunShortId, humanizeRunSummary, formatRunCommandDetail } from './run-display';
import { isAutoCompleteRunSummary } from './operator-run-strip-view';

export type OperatorRadarTone = 'nominal' | 'watch' | 'attention' | 'degraded';
export type OperatorStatusMetricTone = 'default' | 'ok' | 'warn' | 'attention';

export interface OperatorStatusMetric {
  label: string;
  value: string;
  tone: OperatorStatusMetricTone;
}

export interface OperatorMissionSummary {
  runId: string;
  displayName: string;
  shortId: string;
  identityLabel: string;
  phase: string;
  workspace: string;
  status: string;
  elapsed: string;
  currentStep: string;
  watchConnected: boolean;
}

export interface OperatorMissionStep {
  label: string;
  tone: 'done' | 'active' | 'pending';
  meta?: string;
}

export interface OperatorMissionCard {
  label: string;
  value: string;
  tone: OperatorStatusMetricTone;
}

export interface OperatorMissionChip {
  label: string;
  value: string;
  tone: OperatorStatusMetricTone;
}

export interface OperatorExecutionStage {
  runId: string;
  displayName: string;
  shortId: string;
  identityLabel: string;
  phase: string;
  phaseProgress: number;
  summary: string;
  commandDetail: string | null;
  currentStep: string;
  notice: string;
  advise: string;
  decide: string;
  elapsed: string;
  hasActiveRun: boolean;
}

export interface OperatorLiveFeedItem {
  id: string;
  label: string;
  meta?: string;
  tone: 'done' | 'active' | 'info' | 'pending';
}

export interface OperatorStatusRailItem {
  label: string;
  value: string;
  tone: OperatorStatusMetricTone;
}

export type OperatorStatusLoadState = 'idle' | 'loading' | 'loaded' | 'error';

function truncatePanelCopy(value: string, maxLength = 96): string {
  const trimmed = value.trim().replace(/\s+/g, ' ');
  if (trimmed.length <= maxLength) {
    return trimmed;
  }
  return `${trimmed.slice(0, maxLength - 1).trimEnd()}…`;
}

function elapsedLabel(startedAt: string | null, endedAt: string | null, updatedAt: string | null): string {
  if (!startedAt) {
    return '—';
  }

  const startMs = Date.parse(startedAt);
  const endMs = Date.parse(endedAt ?? updatedAt ?? startedAt);
  if (!Number.isFinite(startMs) || !Number.isFinite(endMs) || endMs < startMs) {
    return '—';
  }

  const totalSeconds = Math.max(0, Math.round((endMs - startMs) / 1000));
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;

  if (minutes >= 60) {
    const hours = Math.floor(minutes / 60);
    const remMinutes = minutes % 60;
    if (hours >= 48) {
      const days = Math.floor(hours / 24);
      const remHours = hours % 24;
      return `${days}d ${remHours}h`;
    }
    return `${hours}h ${String(remMinutes).padStart(2, '0')}m`;
  }

  if (minutes > 0) {
    return `${minutes}m ${String(seconds).padStart(2, '0')}s`;
  }
  return `${seconds}s`;
}

function firstMeaningfulLine(content: string | null | undefined): string {
  if (!content) {
    return 'No agent output yet';
  }

  const lines = content
    .split('\n')
    .map((line) => line.trim())
    .filter((line) => line.length > 0 && line !== '```');

  return truncatePanelCopy(lines[0] ?? 'No agent output yet');
}

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
  workspaceReviewReadyCount?: number;
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
}): string {
  if (input.loadState === 'loading') {
    return 'Standing by for briefing projection.';
  }

  if (input.loadState === 'error') {
    return 'Review connectivity before dispatching more work.';
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

export function operatorMissionCards(input: {
  runtimeSummary: RuntimeSummary | null;
  briefing: OperatorBriefing | null;
  pendingApprovals: number;
  lastAgentMessage: string | null;
}): OperatorMissionCard[] {
  const openSignals =
    input.briefing?.top_signals.length ?? input.runtimeSummary?.signals.open_count ?? 0;
  const watchConnected =
    input.briefing?.connectivity.watch_connected ?? input.runtimeSummary?.watch.connected ?? false;

  return [
    {
      label: 'Last agent result',
      value: firstMeaningfulLine(input.lastAgentMessage),
      tone: 'default',
    },
    {
      label: 'Runtime summary',
      value: watchConnected ? 'Watch connected · runtime live' : 'Watch disconnected',
      tone: watchConnected ? 'ok' : 'warn',
    },
    {
      label: 'Signals',
      value: openSignals > 0 ? `${openSignals} open attention item(s)` : 'No open signals',
      tone: openSignals > 0 ? 'attention' : 'default',
    },
    {
      label: 'Approval boundary',
      value:
        input.pendingApprovals > 0
          ? `${input.pendingApprovals} approval(s) pending`
          : 'No approval boundary open',
      tone: input.pendingApprovals > 0 ? 'attention' : 'ok',
    },
  ];
}

export function operatorExecutionStage(input: {
  workspaceId: string | null;
  runtimeSummary: RuntimeSummary | null;
  briefing: OperatorBriefing | null;
  loadState: OperatorStatusLoadState;
  primaryActiveRun: RunRecord | null;
  workspaceReviewReadyCount?: number;
}): OperatorExecutionStage {
  const mission = operatorMissionSummary({
    workspaceId: input.workspaceId,
    runtimeSummary: input.runtimeSummary,
    primaryActiveRun: input.primaryActiveRun,
  });
  const run = input.primaryActiveRun;

  return {
    runId: mission.runId,
    displayName: mission.displayName,
    shortId: mission.shortId,
    identityLabel: mission.identityLabel,
    phase: mission.phase,
    phaseProgress: runPhaseProgress(run?.phase ?? null),
    summary: run ? humanizeRunSummary(run.summary) : 'Standing by for the next command.',
    commandDetail: run ? formatRunCommandDetail(run) : null,
    currentStep: mission.currentStep,
    notice: operatorStatusHeadline({
      briefing: input.briefing,
      loadState: input.loadState,
      primaryActiveRun: run,
      workspaceReviewReadyCount: input.workspaceReviewReadyCount,
    }),
    advise: operatorStatusAdvise({
      briefing: input.briefing,
      loadState: input.loadState,
    }),
    decide:
      input.briefing?.executive_rhythm?.decide ??
      'Decide whether to continue from the current operator posture.',
    elapsed: mission.elapsed,
    hasActiveRun: Boolean(run),
  };
}

export function operatorLiveFeed(input: {
  historyRows: RunHistoryRow[];
  currentStep: string | null;
  lastAgentMessage: string | null;
  advise: string;
  hasActiveRun: boolean;
}): OperatorLiveFeedItem[] {
  const items: OperatorLiveFeedItem[] = [];

  for (const row of [...input.historyRows].reverse().slice(-4)) {
    items.push({
      id: row.id,
      label: truncatePanelCopy(row.label, 120),
      meta: row.timestamp,
      tone: 'done',
    });
  }

  if (input.currentStep) {
    items.push({
      id: 'current-step',
      label: truncatePanelCopy(input.currentStep, 120),
      meta: 'Now executing',
      tone: 'active',
    });
  }

  if (input.lastAgentMessage) {
    const excerpt = firstMeaningfulLine(input.lastAgentMessage);
    const alreadyShown = items.some((item) => item.label === excerpt);
    if (!alreadyShown) {
      items.push({
        id: 'agent-output',
        label: excerpt,
        meta: 'Latest agent output',
        tone: 'info',
      });
    }
  }

  if (!input.hasActiveRun && input.advise) {
    items.push({
      id: 'next-action',
      label: truncatePanelCopy(input.advise, 120),
      meta: 'Suggested next step',
      tone: 'pending',
    });
  }

  if (items.length === 0) {
    items.push({
      id: 'idle',
      label: 'No execution activity yet. Send a command from the dock.',
      meta: 'Idle',
      tone: 'pending',
    });
  }

  return items.slice(-6);
}

export function operatorStatusRail(input: {
  workspaceId: string | null;
  runtimeSummary: RuntimeSummary | null;
  briefing: OperatorBriefing | null;
  pendingApprovals: number;
}): OperatorStatusRailItem[] {
  const watchConnected =
    input.briefing?.connectivity.watch_connected ?? input.runtimeSummary?.watch.connected ?? false;
  const controlPlaneReady =
    input.briefing?.connectivity.control_plane_ready ??
    input.runtimeSummary?.control_plane.ready ??
    false;
  const openSignals =
    input.briefing?.top_signals.length ?? input.runtimeSummary?.signals.open_count ?? 0;

  return [
    {
      label: 'Watch',
      value: watchConnected ? 'online' : 'offline',
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
    {
      label: 'Workspace',
      value: input.workspaceId ?? 'none selected',
      tone: input.workspaceId ? 'default' : 'warn',
    },
  ];
}

export function operatorMissionChips(input: {
  lastReceipt: string | null;
  advise: string;
  runtimeSummary: RuntimeSummary | null;
  briefing: OperatorBriefing | null;
  pendingApprovals: number;
}): OperatorMissionChip[] {
  const openSignals =
    input.briefing?.top_signals.length ?? input.runtimeSummary?.signals.open_count ?? 0;
  const risk =
    input.briefing?.degraded.active || input.runtimeSummary?.degraded.active
      ? 'Runtime degraded'
      : input.pendingApprovals > 0
        ? 'Approval boundary open'
        : openSignals > 0
          ? 'Open signal requires review'
          : 'Nominal';

  return [
    {
      label: 'Last action',
      value: truncatePanelCopy(input.lastReceipt ?? 'No receipts yet', 68),
      tone: 'default',
    },
    {
      label: 'Next action',
      value: truncatePanelCopy(input.advise || 'Await operator input', 68),
      tone: 'warn',
    },
    {
      label: 'Risk',
      value: risk,
      tone: risk === 'Nominal' ? 'ok' : 'attention',
    },
  ];
}
