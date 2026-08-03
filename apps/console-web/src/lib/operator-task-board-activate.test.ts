import { describe, expect, it } from 'vitest';

import {
  resolveTaskBoardCardActivation,
  taskBoardRowShowsBlockingChips,
} from './operator-task-board-activate';
import type { TaskBoardRow } from './operator-task-board-view';

function row(overrides: Partial<TaskBoardRow>): TaskBoardRow {
  return {
    taskId: 'task-1',
    goal: 'Goal',
    goalFull: 'Goal full',
    ownerRole: 'integrations',
    status: 'open',
    bucket: 'open',
    column: 'waiting',
    meta: '',
    attemptsLabel: '0/2',
    canCancel: true,
    canRetry: false,
    canStart: true,
    runId: null,
    acceptance: '',
    risk: 'normal',
    attemptBudget: 2,
    attemptsUsed: 0,
    leaseHolder: null,
    leaseExpiresAt: null,
    terminalOutcome: null,
    allowedPaths: [],
    exclusivePaths: [],
    dependencyIds: [],
    dependencyChips: [],
    blockedByOpenDeps: false,
    planId: null,
    planKey: null,
    planGoal: null,
    planLabel: null,
    planAwaitingEngagement: false,
    archived: false,
    nextActionLabel: 'Start',
    nextActionHint: '',
    nextActionTone: 'start',
    updatedAt: '2026-07-30T20:00:00Z',
    createdAt: '2026-07-30T20:00:00Z',
    ...overrides,
  };
}

describe('resolveTaskBoardCardActivation', () => {
  it('opens failure review for Needs attention cards', () => {
    expect(
      resolveTaskBoardCardActivation(
        row({
          status: 'failed',
          bucket: 'failed',
          column: 'needs_attention',
          canStart: false,
          canRetry: true,
          runId: 'run_fail',
        }),
      ),
    ).toEqual({
      kind: 'open_failure',
      row: expect.objectContaining({ taskId: 'task-1' }),
    });
  });

  it('opens VAXON review for Done cards awaiting Lead engagement', () => {
    expect(
      resolveTaskBoardCardActivation(
        row({
          status: 'completed',
          bucket: 'done',
          column: 'done',
          canStart: false,
          planId: 'plan_1',
          planAwaitingEngagement: true,
        }),
      ),
    ).toEqual({ kind: 'open_vaxon_review', planId: 'plan_1' });
  });

  it('opens the associated run for ordinary Done cards', () => {
    expect(
      resolveTaskBoardCardActivation(
        row({
          status: 'completed',
          bucket: 'done',
          column: 'done',
          canStart: false,
          runId: 'run_done',
        }),
      ),
    ).toEqual({
      kind: 'open_run',
      row: expect.objectContaining({ runId: 'run_done' }),
    });
  });

  it('jumps to the blocking prerequisite for blocked Waiting cards', () => {
    expect(
      resolveTaskBoardCardActivation(
        row({
          canStart: false,
          blockedByOpenDeps: true,
          dependencyChips: [
            {
              taskId: 'task-blocker',
              goal: 'task-3d95eb0',
              status: 'open',
              blocking: true,
            },
          ],
        }),
      ),
    ).toEqual({ kind: 'focus_blocker', blockerTaskId: 'task-blocker' });
  });
});

describe('taskBoardRowShowsBlockingChips', () => {
  it('hides blocking chips on completed Done tickets', () => {
    expect(
      taskBoardRowShowsBlockingChips(
        row({ status: 'completed', bucket: 'done', column: 'done' }),
      ),
    ).toBe(false);
    expect(taskBoardRowShowsBlockingChips(row({ status: 'open' }))).toBe(true);
  });
});
