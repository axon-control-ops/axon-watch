import type { RunRecord, RuntimeSummary } from '../contracts/canonical';

export type RuntimeStripChipTone = 'default' | 'run' | 'success' | 'warning' | 'degraded' | 'muted';

export interface RuntimeStripChip {
  id: 'run' | 'watch' | 'degraded' | 'loading' | 'unavailable';
  label: string;
  tone: RuntimeStripChipTone;
}

export type StatusBarSegmentTone = 'default' | 'success' | 'warning' | 'degraded' | 'high';

export interface StatusBarSegment {
  id: string;
  label: string;
  tone: StatusBarSegmentTone;
}

export type RuntimeSummaryLoadState = 'idle' | 'loading' | 'loaded' | 'error';

function truncateRunId(runId: string, maxLength = 14): string {
  if (runId.length <= maxLength) {
    return runId;
  }
  return `${runId.slice(0, maxLength)}…`;
}

export function buildActiveRunChipLabel(run: RunRecord | null): string | null {
  if (!run) {
    return null;
  }
  return `${truncateRunId(run.run_id)} · ${run.phase}`;
}

export function buildTopbarChips(input: {
  runtimeSummary: RuntimeSummary | null;
  runtimeSummaryLoadState: RuntimeSummaryLoadState;
  primaryActiveRun: RunRecord | null;
}): RuntimeStripChip[] {
  if (input.runtimeSummaryLoadState === 'loading') {
    return [{ id: 'loading', label: 'Loading runtime…', tone: 'muted' }];
  }

  if (input.runtimeSummaryLoadState === 'error') {
    return [{ id: 'unavailable', label: 'Runtime unavailable', tone: 'warning' }];
  }

  if (!input.runtimeSummary) {
    return [{ id: 'loading', label: 'Awaiting runtime…', tone: 'muted' }];
  }

  const chips: RuntimeStripChip[] = [];
  const runLabel = buildActiveRunChipLabel(input.primaryActiveRun);
  if (runLabel) {
    chips.push({ id: 'run', label: runLabel, tone: 'run' });
  }

  const watch = input.runtimeSummary.watch;
  if (watch.connected) {
    chips.push({ id: 'watch', label: 'watch connected', tone: 'success' });
  } else {
    chips.push({ id: 'watch', label: 'watch offline', tone: 'warning' });
  }

  if (input.runtimeSummary.degraded.active) {
    const reason = input.runtimeSummary.degraded.reasons[0] ?? 'degraded';
    chips.push({ id: 'degraded', label: `degraded · ${reason}`, tone: 'degraded' });
  }

  return chips.slice(0, 3);
}

export function buildStatusBarSegments(input: {
  layoutModeLabel: string;
  workspaceId: string | null;
  runtimeSummary: RuntimeSummary | null;
  pendingApprovals: number;
}): StatusBarSegment[] {
  const segments: StatusBarSegment[] = [
    { id: 'mode', label: input.layoutModeLabel, tone: 'default' },
  ];

  if (input.workspaceId) {
    segments.push({ id: 'workspace', label: input.workspaceId, tone: 'default' });
  }

  if (input.runtimeSummary) {
    const watch = input.runtimeSummary.watch;
    if (watch.connected) {
      segments.push({ id: 'watch', label: 'watch connected', tone: 'success' });
    } else if (input.runtimeSummary.degraded.active) {
      segments.push({ id: 'watch', label: 'watch degraded', tone: 'degraded' });
    } else {
      segments.push({ id: 'watch', label: 'watch offline', tone: 'warning' });
    }

    const openSignals = input.runtimeSummary.signals.open_count;
    if (openSignals > 0) {
      const severityHint =
        input.runtimeSummary.signals.critical_count > 0
          ? 'critical'
          : input.runtimeSummary.signals.high_count > 0
            ? 'high'
            : 'open';
      segments.push({
        id: 'signals',
        label: `signals: ${openSignals} · ${severityHint}`,
        tone:
          input.runtimeSummary.signals.critical_count > 0
            ? 'high'
            : input.runtimeSummary.signals.high_count > 0
              ? 'warning'
              : 'default',
      });
    }

    if (input.pendingApprovals > 0) {
      segments.push({
        id: 'approvals',
        label: `approvals: ${input.pendingApprovals}`,
        tone: 'warning',
      });
    }

    if (input.runtimeSummary.degraded.active) {
      segments.push({
        id: 'degraded',
        label: input.runtimeSummary.degraded.reasons[0] ?? 'degraded',
        tone: 'degraded',
      });
    }
  }

  return segments;
}
