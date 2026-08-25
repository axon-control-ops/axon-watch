import { describe, expect, it } from 'vitest';

import type { WorkspaceTaskRecord } from '../api/tasks-api';
import {
  humanizeHandoffBlockedReason,
  taskDependenciesCompleted,
  taskDependencyBlockerMessage,
} from './task-dependencies';

function task(overrides: Partial<WorkspaceTaskRecord> = {}): WorkspaceTaskRecord {
  return {
    task_id: 'task_child',
    workspace_id: 'workspace_dashpro',
    goal: 'Lead follow-up',
    acceptance_criteria: '',
    owner_role: 'lead',
    status: 'open',
    risk: 'normal',
    attempt_budget: 3,
    attempts_used: 0,
    dependencies: [],
    allowed_paths: [],
    exclusive_paths: [],
    lease_holder: null,
    lease_expires_at: null,
    run_id: null,
    plan_id: null,
    plan_key: null,
    terminal_outcome: null,
    created_at: '2026-07-30T00:00:00Z',
    updated_at: '2026-07-30T00:00:00Z',
    ...overrides,
  };
}

describe('taskDependenciesCompleted', () => {
  it('treats only completed dependencies as satisfied', () => {
    const completed = task({
      task_id: 'task_done',
      status: 'completed',
      owner_role: 'backend',
    });
    const cancelled = task({
      task_id: 'task_cancelled',
      status: 'cancelled',
      owner_role: 'backend',
    });
    const byId = new Map([
      [completed.task_id, completed],
      [cancelled.task_id, cancelled],
    ]);

    expect(
      taskDependenciesCompleted(task({ dependencies: [completed.task_id] }), byId),
    ).toBe(true);
    expect(
      taskDependenciesCompleted(task({ dependencies: [cancelled.task_id] }), byId),
    ).toBe(false);
  });

  it('builds operator-facing blocker messages', () => {
    const blocker = task({
      task_id: 'task_verify',
      owner_role: 'backend',
      goal: 'Verification after Marco backend work',
      status: 'open',
    });
    const byId = new Map([[blocker.task_id, blocker]]);
    const child = task({ dependencies: [blocker.task_id] });

    expect(taskDependencyBlockerMessage(child, byId)).toContain('backend task_verify (open)');
    expect(humanizeHandoffBlockedReason(child, byId)).toContain(
      'Waiting on backend verification',
    );
  });
});
