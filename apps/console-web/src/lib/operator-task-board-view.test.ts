import { describe, expect, it } from 'vitest';

import type { WorkspaceTaskRecord } from '../api/tasks-api';
import {
  buildOperatorTaskBoardView,
  columnForTask,
  filterTaskBoardRows,
  summarizeTaskBoardLabel,
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
  it('places tasks into plan-aware columns without drag semantics', () => {
    const view = buildOperatorTaskBoardView(
      [
        task({
          task_id: 'task-open',
          goal: 'Open work',
          status: 'open',
          updated_at: '2026-07-22T12:02:00Z',
        }),
        task({
          task_id: 'task-leased',
          goal: 'Live work',
          status: 'leased',
          lease_holder: 'backend-1',
          updated_at: '2026-07-22T12:03:00Z',
        }),
        task({
          task_id: 'task-done',
          goal: 'Finished',
          status: 'completed',
          updated_at: '2026-07-22T12:01:00Z',
        }),
        task({
          task_id: 'task-failed',
          goal: 'Broken',
          status: 'failed',
          updated_at: '2026-07-22T12:04:00Z',
        }),
        task({
          task_id: 'task-cancelled',
          goal: 'Stopped',
          status: 'cancelled',
          updated_at: '2026-07-22T11:00:00Z',
        }),
      ],
      [
        {
          plan_id: 'lead-plan-1',
          workspace_id: 'workspace_dashpro',
          goal: 'Ship Gate 5',
          mode: 'fan_out',
          status: 'active',
          plan: {},
          supersedes_plan_id: null,
          created_at: '2026-07-22T11:00:00Z',
          updated_at: '2026-07-22T12:00:00Z',
          task_links: [
            { plan_key: 'backend', task_id: 'task-open' },
            { plan_key: 'frontend', task_id: 'task-leased' },
          ],
          task_ids: ['task-open', 'task-leased'],
          awaiting_engagement: false,
        },
      ],
    );

    expect(view.counts.waiting).toBe(1);
    expect(view.counts.inProgress).toBe(1);
    expect(view.counts.done).toBe(1);
    expect(view.counts.needsAttention).toBe(1);
    expect(view.counts.cancelled).toBe(1);
    expect(view.columns.map((column) => column.id)).toEqual([
      'waiting',
      'in_progress',
      'done',
      'needs_attention',
    ]);
    expect(view.historyRows).toHaveLength(1);
    expect(view.planGroups.some((group) => group.planId === 'lead-plan-1')).toBe(true);
  });

  it('shortens Lead fan-out essays into plan chip labels', () => {
    const longGoal =
      'Check with all sub-agents and fan out this corrected graduation readiness cut — real work, thin slices. • Marco (backend): Confirm roster. • Priya (frontend): UI caller.';
    const view = buildOperatorTaskBoardView(
      [
        task({
          task_id: 'task-open',
          goal: 'Open work',
          status: 'open',
          plan_id: 'lead-plan-long',
        }),
      ],
      [
        {
          plan_id: 'lead-plan-long',
          workspace_id: 'workspace_dashpro',
          goal: longGoal,
          mode: 'fan_out',
          status: 'active',
          plan: {},
          supersedes_plan_id: null,
          created_at: '2026-07-22T11:00:00Z',
          updated_at: '2026-07-22T12:00:00Z',
          task_links: [{ plan_key: 'backend', task_id: 'task-open' }],
          task_ids: ['task-open'],
          awaiting_engagement: true,
        },
      ],
    );
    const group = view.planGroups.find((item) => item.planId === 'lead-plan-long');
    expect(group?.planGoal).toBe(longGoal);
    expect(group?.planLabel.length).toBeLessThan(60);
    expect(group?.planLabel).toMatch(/^Check with all sub-agents/i);
    expect(group?.planLabel).not.toContain('Marco (backend)');
    expect(view.rows[0]?.planLabel).toBe(group?.planLabel);
  });

  it('summarizes plan labels without dumping the whole fan-out', () => {
    expect(
      summarizeTaskBoardLabel(
        'Ship Gate 5. Then verify CI. Then hand off to integrations.',
        40,
      ),
    ).toBe('Ship Gate 5.');
    expect(summarizeTaskBoardLabel('Short', 40)).toBe('Short');
  });

  it('marks open dependencies as blocking chips', () => {
    const view = buildOperatorTaskBoardView([
      task({
        task_id: 'task-dep',
        goal: 'Dependency',
        status: 'open',
      }),
      task({
        task_id: 'task-blocked',
        goal: 'Blocked work',
        status: 'open',
        dependencies: ['task-dep'],
      }),
    ]);
    const blocked = view.rows.find((row) => row.taskId === 'task-blocked');
    expect(blocked?.blockedByOpenDeps).toBe(true);
    expect(blocked?.dependencyChips[0]?.blocking).toBe(true);
  });
});

describe('columnForTask', () => {
  it('keeps cancelled off the live columns', () => {
    expect(columnForTask(task({ task_id: 'c', goal: 'c', status: 'cancelled' }))).toBeNull();
    expect(columnForTask(task({ task_id: 'f', goal: 'f', status: 'failed' }))).toBe(
      'needs_attention',
    );
  });
});

describe('filterTaskBoardRows', () => {
  it('hides cancelled from the default board filter', () => {
    const view = buildOperatorTaskBoardView([
      task({ task_id: 'task-done', goal: 'Done', status: 'completed' }),
      task({ task_id: 'task-cancelled', goal: 'Cancelled', status: 'cancelled' }),
    ]);
    expect(filterTaskBoardRows(view.rows, 'board')).toHaveLength(1);
    expect(filterTaskBoardRows(view.rows, 'history')).toHaveLength(2);
  });
});
