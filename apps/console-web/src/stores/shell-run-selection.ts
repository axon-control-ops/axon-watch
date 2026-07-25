import type { RunRecord } from '../contracts/canonical';

const TERMINAL_PHASES = new Set(['completed', 'failed', 'cancelled']);

export function isActiveRun(run: RunRecord): boolean {
  return !TERMINAL_PHASES.has(run.phase);
}

/** Prefer the run that needs operator action; deprioritize approval-bound runs for the run seam. */
export function selectPrimaryRun(items: RunRecord[]): RunRecord | null {
  const activeRuns = items.filter(isActiveRun);
  if (activeRuns.length === 0) {
    return null;
  }

  const reviewReady = activeRuns.find((run) => run.phase === 'review_ready');
  if (reviewReady) {
    return reviewReady;
  }

  const nonApprovalRun = activeRuns.find((run) => run.phase !== 'awaiting_approval');
  return nonApprovalRun ?? activeRuns[0] ?? null;
}

/** Dedicated approval target so guarded runs stay visible when another run is active. */
export function selectPrimaryApprovalRun(items: RunRecord[]): RunRecord | null {
  return items.find((run) => run.phase === 'awaiting_approval') ?? null;
}

/** Workspace-scoped primary run: only non-terminal runs; null when the workspace is idle. */
export function selectWorkspacePrimaryRun(items: RunRecord[]): RunRecord | null {
  return selectPrimaryRun(items.filter(isActiveRun));
}

function runSortTimestamp(run: Pick<RunRecord, 'started_at' | 'updated_at'>): string {
  return run.updated_at || run.started_at;
}

/** Most recently touched run in the provided workspace-scoped list. */
export function selectLatestWorkspaceRun(items: RunRecord[]): RunRecord | null {
  if (items.length === 0) {
    return null;
  }

  return [...items].sort((left, right) =>
    runSortTimestamp(right).localeCompare(runSortTimestamp(left)),
  )[0] ?? null;
}

export function isRunOnLocalCalendarDay(
  run: Pick<RunRecord, 'started_at' | 'updated_at'>,
  reference = new Date(),
): boolean {
  const stamp = runSortTimestamp(run);
  if (!stamp) {
    return false;
  }

  const runDate = new Date(stamp);
  return (
    runDate.getFullYear() === reference.getFullYear() &&
    runDate.getMonth() === reference.getMonth() &&
    runDate.getDate() === reference.getDate()
  );
}

/** Active run when one exists; otherwise the latest completed run from today. */
export function selectRunSeamDisplayRun(items: RunRecord[]): RunRecord | null {
  const active = selectWorkspacePrimaryRun(items);
  if (active) {
    return active;
  }

  const latest = selectLatestWorkspaceRun(items);
  if (!latest || !isRunOnLocalCalendarDay(latest)) {
    return null;
  }

  return latest;
}

/** History target: active run, then explicit linked run, then latest workspace run. */
export function resolveRunHistoryRunId(
  items: RunRecord[],
  preferredRunId?: string | null,
): string | null {
  const active = selectWorkspacePrimaryRun(items);
  if (active) {
    return active.run_id;
  }

  if (preferredRunId) {
    const preferred = items.find((run) => run.run_id === preferredRunId);
    if (preferred) {
      return preferred.run_id;
    }
  }

  return selectLatestWorkspaceRun(items)?.run_id ?? null;
}
