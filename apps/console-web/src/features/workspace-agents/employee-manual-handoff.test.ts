import { describe, expect, it } from 'vitest';

import type { CompanyEmployeeRecord } from '../../contracts/canonical';
import type { WorkspaceTaskRecord } from '../../api/tasks-api';
import { resolveEmployeeManualHandoff } from './employee-manual-handoff';

function employee(overrides: Partial<CompanyEmployeeRecord> = {}): CompanyEmployeeRecord {
  return {
    employee_id: 'employee-soren',
    workspace_id: 'workspace_dashpro',
    name: 'Soren',
    role: 'integrations',
    role_label: 'Integrations',
    schedule: 'continuous',
    schedule_label: 'Continuous',
    status: 'idle',
    owns: 'OTA',
    enabled: true,
    primary: false,
    ...overrides,
  };
}

function task(overrides: Partial<WorkspaceTaskRecord> = {}): WorkspaceTaskRecord {
  return {
    task_id: 'task_1',
    workspace_id: 'workspace_dashpro',
    goal: 'Own operator-canary EAS/OTA publish',
    acceptance_criteria: '',
    owner_role: 'integrations',
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

describe('resolveEmployeeManualHandoff', () => {
  it('shows waiting Start now in Manual for any open unblocked role task', () => {
    const row = employee();
    const tasks = [task()];
    expect(
      resolveEmployeeManualHandoff({
        employee: row,
        autonomyMode: 'manual',
        tasks,
      }),
    ).toEqual({
      waiting: true,
      taskId: 'task_1',
      reason: 'open_task',
      blockedReason: null,
    });
    expect(
      resolveEmployeeManualHandoff({
        employee: row,
        autonomyMode: 'full',
        tasks,
      }).waiting,
    ).toBe(false);
  });

  it('hides Start now when an open task has exhausted its attempt budget', () => {
    expect(
      resolveEmployeeManualHandoff({
        employee: employee({ role: 'lead', name: 'Imani' }),
        autonomyMode: 'manual',
        tasks: [task({ owner_role: 'lead', attempt_budget: 2, attempts_used: 2 })],
      }),
    ).toEqual({ waiting: false, taskId: null, reason: null, blockedReason: null });
  });

  it('hides Semi Start now for ordinary open tasks without handoff provenance', () => {
    expect(
      resolveEmployeeManualHandoff({
        employee: employee(),
        autonomyMode: 'semi',
        tasks: [task()],
      }).waiting,
    ).toBe(false);
  });

  it('shows Semi Start now for cross-workspace handoff tickets', () => {
    expect(
      resolveEmployeeManualHandoff({
        employee: employee({ role: 'frontend', name: 'Priya' }),
        autonomyMode: 'semi',
        tasks: [
          task({
            owner_role: 'frontend',
            acceptance_criteria:
              'Complete the cross-workspace handoff from Young Eagles Day Care.',
          }),
        ],
      }),
    ).toEqual({
      waiting: true,
      taskId: 'task_1',
      reason: 'open_task',
      blockedReason: null,
    });
  });

  it('shows Semi Start now for open Lead board tickets', () => {
    expect(
      resolveEmployeeManualHandoff({
        employee: employee({ role: 'lead', name: 'Dana', status: 'idle' }),
        autonomyMode: 'semi',
        tasks: [task({ owner_role: 'lead', goal: 'Lead board ticket' })],
      }),
    ).toEqual({
      waiting: true,
      taskId: 'task_1',
      reason: 'open_task',
      blockedReason: null,
    });
  });

  it('treats assigned specialists as handoff waiters in Manual', () => {
    expect(
      resolveEmployeeManualHandoff({
        employee: employee({ status: 'assigned' }),
        autonomyMode: 'manual',
        tasks: [
          task({
            status: 'leased',
            run_id: 'run_queued',
            lease_holder: 'operator-start-workspace_dashpro-integrations',
          }),
        ],
      }),
    ).toMatchObject({
      waiting: true,
      reason: 'assigned',
      taskId: 'task_1',
      blockedReason: null,
    });
  });

  it('starts the assigned run task before an unrelated newer open task', () => {
    const assigned = task({
      task_id: 'task_assigned',
      status: 'leased',
      run_id: 'run_assigned',
      updated_at: '2026-07-30T14:00:00Z',
    });
    const unrelated = task({
      task_id: 'task_unrelated',
      status: 'open',
      updated_at: '2026-07-30T15:00:00Z',
    });

    expect(
      resolveEmployeeManualHandoff({
        employee: employee({
          status: 'assigned',
          active_run_id: 'run_assigned',
        }),
        autonomyMode: 'manual',
        tasks: [unrelated, assigned],
      }),
    ).toEqual({
      waiting: true,
      taskId: 'task_assigned',
      reason: 'assigned',
      blockedReason: null,
    });
  });

  it('resolves an assigned task from runs while the task snapshot is stale', () => {
    expect(
      resolveEmployeeManualHandoff({
        employee: employee({
          status: 'assigned',
          active_run_id: 'run_assigned',
        }),
        autonomyMode: 'manual',
        tasks: [],
        runs: [{ run_id: 'run_assigned', task_id: 'task_assigned' }],
      }),
    ).toEqual({
      waiting: true,
      taskId: 'task_assigned',
      reason: 'assigned',
      blockedReason: null,
    });
  });

  it('hides Start now when dependencies are cancelled instead of completed', () => {
    const cancelled = task({
      task_id: 'task_cancelled',
      status: 'cancelled',
      owner_role: 'backend',
      goal: 'Verification after Marco backend work',
    });
    const leadFollowUp = task({
      task_id: 'task_lead',
      owner_role: 'lead',
      dependencies: [cancelled.task_id],
    });
    expect(
      resolveEmployeeManualHandoff({
        employee: employee({ role: 'lead', name: 'Dana' }),
        autonomyMode: 'semi',
        tasks: [cancelled, leadFollowUp],
      }),
    ).toEqual({
      waiting: false,
      taskId: null,
      reason: null,
      blockedReason: expect.stringContaining('Waiting on backend verification'),
    });
  });

  it('shows Start now for Marco verification tasks in Manual mode', () => {
    const verification = task({
      task_id: 'task_verify',
      owner_role: 'backend',
      goal: 'Verification after Marco backend work',
    });
    expect(
      resolveEmployeeManualHandoff({
        employee: employee({ role: 'backend', name: 'Marco' }),
        autonomyMode: 'manual',
        tasks: [verification],
      }),
    ).toEqual({
      waiting: true,
      taskId: 'task_verify',
      reason: 'open_task',
      blockedReason: null,
    });
  });

  it('shows Semi Start now for specialist verification handoffs', () => {
    const verification = task({
      task_id: 'task_verify',
      owner_role: 'backend',
      goal: 'Verification after Marco (backend): npm test',
    });
    expect(
      resolveEmployeeManualHandoff({
        employee: employee({ role: 'backend', name: 'Marco' }),
        autonomyMode: 'semi',
        tasks: [verification],
      }),
    ).toEqual({
      waiting: true,
      taskId: 'task_verify',
      reason: 'open_task',
      blockedReason: null,
    });
  });

  it('does not glow when assigned has no actionable task', () => {
    expect(
      resolveEmployeeManualHandoff({
        employee: employee({ status: 'assigned' }),
        autonomyMode: 'manual',
        tasks: [],
      }),
    ).toEqual({ waiting: false, taskId: null, reason: null, blockedReason: null });
  });

  it('hides Start now when the teammate is live-busy even with an open handoff', () => {
    expect(
      resolveEmployeeManualHandoff({
        employee: employee({ status: 'idle', role: 'watcher', name: 'Cass' }),
        autonomyMode: 'manual',
        tasks: [task({ owner_role: 'watcher' })],
        liveBusy: true,
      }),
    ).toEqual({ waiting: false, taskId: null, reason: null, blockedReason: null });
  });

  it('hides Start now when a continuous worker is mid-shift with an open handoff', () => {
    expect(
      resolveEmployeeManualHandoff({
        employee: employee({
          status: 'watching',
          role: 'watcher',
          name: 'Cass',
          active_run_id: 'run_busy',
        }),
        autonomyMode: 'manual',
        tasks: [task({ owner_role: 'watcher' })],
      }),
    ).toEqual({ waiting: false, taskId: null, reason: null, blockedReason: null });
  });

  it('hides Start now while executing even if an assigned lease is still bound', () => {
    expect(
      resolveEmployeeManualHandoff({
        employee: employee({
          status: 'executing',
          active_run_id: 'run_assigned',
        }),
        autonomyMode: 'manual',
        tasks: [
          task({
            status: 'leased',
            run_id: 'run_assigned',
          }),
        ],
      }),
    ).toEqual({ waiting: false, taskId: null, reason: null, blockedReason: null });
  });

  it('still shows Start now for assigned leases that are not busy yet', () => {
    expect(
      resolveEmployeeManualHandoff({
        employee: employee({ status: 'assigned' }),
        autonomyMode: 'manual',
        tasks: [
          task({
            status: 'leased',
            run_id: 'run_queued',
          }),
        ],
        liveBusy: false,
      }),
    ).toMatchObject({
      waiting: true,
      reason: 'assigned',
      taskId: 'task_1',
      blockedReason: null,
    });
  });

  it('shows Run verification after a failed leased verification shift', () => {
    expect(
      resolveEmployeeManualHandoff({
        employee: employee({ role: 'backend', name: 'Marco', status: 'idle' }),
        autonomyMode: 'manual',
        tasks: [
          task({
            task_id: 'task_verify_failed',
            owner_role: 'backend',
            status: 'leased',
            run_id: 'run_failed_verify',
            goal: 'Verification after Marco (backend): npm test',
          }),
        ],
      }),
    ).toEqual({
      waiting: true,
      taskId: 'task_verify_failed',
      reason: 'open_task',
      blockedReason: null,
    });
  });

  it('shows Run verification when active_run_id remains set after gate 6 fail', () => {
    expect(
      resolveEmployeeManualHandoff({
        employee: employee({
          role: 'backend',
          name: 'Marco',
          status: 'idle',
          active_run_id: 'run_failed_verify',
          last_outcome: 'failed',
          last_outcome_detail: 'acceptance_evidence did not pass (Gate 6)',
        }),
        autonomyMode: 'manual',
        tasks: [
          task({
            task_id: 'task_verify_failed',
            owner_role: 'backend',
            status: 'leased',
            run_id: 'run_failed_verify',
            goal: 'Verification after Marco (backend): npm test',
          }),
        ],
      }),
    ).toMatchObject({
      waiting: true,
      taskId: 'task_verify_failed',
    });
  });
});
