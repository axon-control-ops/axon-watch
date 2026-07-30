import type { TaskBoardRow } from './operator-task-board-view';

export type TaskBoardCardActivation =
  | { kind: 'start'; taskId: string }
  | { kind: 'open_failure'; row: TaskBoardRow }
  | { kind: 'open_run'; row: TaskBoardRow }
  | { kind: 'open_specialist'; row: TaskBoardRow }
  | { kind: 'open_vaxon_review'; planId: string }
  | { kind: 'focus_blocker'; blockerTaskId: string }
  | { kind: 'select'; taskId: string };

/**
 * What a card click should do. Waiting Start stays on the Start button;
 * Needs attention / Done / blocked cards must not be silent selects only.
 */
export function resolveTaskBoardCardActivation(row: TaskBoardRow): TaskBoardCardActivation {
  if (row.status === 'failed' || row.column === 'needs_attention') {
    return { kind: 'open_failure', row };
  }
  if (row.status === 'completed' && row.planAwaitingEngagement && row.planId) {
    return { kind: 'open_vaxon_review', planId: row.planId };
  }
  if (row.status === 'completed') {
    if (row.runId) {
      return { kind: 'open_run', row };
    }
    return { kind: 'open_specialist', row };
  }
  if (row.status === 'open' && row.blockedByOpenDeps) {
    const blocker = row.dependencyChips.find((chip) => chip.blocking);
    if (blocker?.taskId) {
      return { kind: 'focus_blocker', blockerTaskId: blocker.taskId };
    }
  }
  if (row.canStart) {
    // Keep Start on the dedicated control; card click still opens details.
    return { kind: 'select', taskId: row.taskId };
  }
  if (row.status === 'leased' && row.runId) {
    return { kind: 'open_run', row };
  }
  return { kind: 'select', taskId: row.taskId };
}

/** Terminal tickets should not look "blocked" by unfinished prerequisites. */
export function taskBoardRowShowsBlockingChips(row: TaskBoardRow): boolean {
  return row.status === 'open' || row.status === 'leased';
}
