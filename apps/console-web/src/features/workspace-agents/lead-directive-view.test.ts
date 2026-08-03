import { describe, expect, it } from 'vitest';

import type { WorkspaceTaskRecord } from '../../api/tasks-api';
import { resolveLeadDirective } from './lead-directive-view';

function task(overrides: Partial<WorkspaceTaskRecord>): WorkspaceTaskRecord {
  return {
    task_id: 'task_lead',
    workspace_id: 'workspace_dashpro',
    goal: 'Lead: review the failed CI receipt and assign the recovery [from run run_123]',
    acceptance_criteria: '',
    risk: 'normal',
    owner_role: 'lead',
    dependencies: [],
    status: 'open',
    lease_holder: null,
    lease_expires_at: null,
    attempt_budget: 2,
    attempts_used: 0,
    terminal_outcome: null,
    run_id: null,
    created_at: '2026-08-03T00:00:00Z',
    updated_at: '2026-08-03T00:00:00Z',
    ...overrides,
  };
}

describe('resolveLeadDirective', () => {
  it('shows a queued Lead recovery as the next planned step', () => {
    expect(resolveLeadDirective([task({})])).toMatchObject({
      phase: 'planning',
      label: 'Planning next step',
      instruction: 'review the failed CI receipt and assign the recovery',
    });
  });

  it('shows a leased Lead task as executing and ignores other owners', () => {
    const result = resolveLeadDirective([
      task({ owner_role: 'backend', updated_at: '2026-08-03T02:00:00Z' }),
      task({ task_id: 'task_running', status: 'leased', updated_at: '2026-08-03T01:00:00Z' }),
    ]);
    expect(result).toMatchObject({
      taskId: 'task_running',
      phase: 'executing',
      label: 'Executing next step',
    });
  });
});
