import type { RunRecord } from '../contracts/canonical';

const TERMINAL_PHASES = new Set(['completed', 'failed', 'cancelled']);

export function isActiveRun(run: RunRecord): boolean {
  return !TERMINAL_PHASES.has(run.phase);
}

/** Prefer the main active run; deprioritize approval-bound runs for the run seam. */
export function selectPrimaryRun(items: RunRecord[]): RunRecord | null {
  const activeRuns = items.filter(isActiveRun);
  if (activeRuns.length === 0) {
    return items[0] ?? null;
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
