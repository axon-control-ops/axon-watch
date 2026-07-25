import { describe, expect, it } from 'vitest';

import type { WorkspaceTaskRecord } from '../api/tasks-api';
import {
  buildOperatorTaskBoardView,
  filterTaskBoardRows,
} from './operator-task-board-view';

function task(
  partial: Partial<WorkspaceTaskRecord> &
    Pick<WorkspaceTaskRecord, 'task_id' | 'goal' | 'status'>,
): WorkspaceTaskRecord {
  return {
    workspace_id: 'workspace_dashpro',
    acceptance_criteria: '',
    risk: 'normal',
    owner_role: 'backend',
    dependencies: [],
    lease_holder: null,
    lease_expires_at: null,
    attempt_budget: 3,
    attempts_used: 0,
    terminal_outcome: null,
    run_id: null,
    created_at: '2026-07-22T12:00:00Z',
    updated_at: '2026-07-22T12:00:00Z',
    ...partial,
  };
}

describe('buildOperatorTaskBoardView', () => {
  it('counts buckets and prefers leased rows first', () => {
    const view = buildOperatorTaskBoardView([
      task({
        task_id: 'task-open',
        goal: 'Open work',
        status: 'open',
        updated_at: '2026-07-22T12:02:00Z',
      }),
      task({
        task_id: 'task-leased',
        goal: 'Leased work',
        status: 'leased',
        lease_holder: 'employee-workspace_dashpro-backend',
        attempts_used: 1,
        updated_at: '2026-07-22T12:01:00Z',
      }),
      task({
        task_id: 'task-done',
        goal: 'Finished',
        status: 'completed',
        terminal_outcome: 'acceptance met',
        updated_at: '2026-07-22T11:00:00Z',
      }),
      task({
        task_id: 'task-cancelled',
        goal: 'Noise',
        status: 'cancelled',
        updated_at: '2026-07-22T13:00:00Z',
      }),
    ]);

    expect(view.counts).toEqual({
      open: 1,
      leased: 1,
      completed: 1,
      failed: 0,
      cancelled: 1,
      total: 4,
    });
    expect(view.headline).toBe('1 leased · 1 waiting');
    expect(view.defaultFilter).toBe('active');
    expect(view.rows[0]?.taskId).toBe('task-leased');
    expect(view.rows[0]?.canCancel).toBe(true);
    expect(view.rows[1]?.taskId).toBe('task-open');
    expect(view.rows.find((row) => row.taskId === 'task-cancelled')?.bucket).toBe(
      'cancelled',
    );
  });

  it('defaults to done when only completed work remains', () => {
    const view = buildOperatorTaskBoardView([
      task({
        task_id: 'task-done',
        goal: 'Finished',
        status: 'completed',
      }),
      task({
        task_id: 'task-cancelled',
        goal: 'Noise',
        status: 'cancelled',
        updated_at: '2026-07-22T13:00:00Z',
      }),
    ]);
    expect(view.defaultFilter).toBe('done');
    expect(view.headline).toBe('1 done');
    expect(filterTaskBoardRows(view.rows, 'done').map((row) => row.taskId)).toEqual([
      'task-done',
    ]);
    expect(filterTaskBoardRows(view.rows, 'active')).toEqual([]);
  });

  it('shows empty copy when ledger is empty', () => {
    const view = buildOperatorTaskBoardView([]);
    expect(view.rows).toEqual([]);
    expect(view.headline).toBe('Nothing queued');
    expect(view.purpose.toLowerCase()).toContain('specialist');
  });
});
