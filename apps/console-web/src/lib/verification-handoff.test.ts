import { describe, expect, it } from 'vitest';

import type { CompanyEmployeeRecord } from '../contracts/canonical';
import type { WorkspaceTaskRecord } from '../api/tasks-api';
import {
  employeeLooksLikeVerificationRetry,
  operatorStartActionLabel,
  resolveOperatorStartAction,
  taskIsVerificationHandoff,
  verificationHandoffActionLabel,
} from './verification-handoff';

function task(goal: string, overrides: Partial<WorkspaceTaskRecord> = {}): WorkspaceTaskRecord {
  return {
    task_id: 'task-1',
    workspace_id: 'workspace_dashpro',
    goal,
    acceptance_criteria: '',
    owner_role: 'backend',
    status: 'open',
    risk: 'normal',
    attempt_budget: 2,
    attempts_used: 0,
    dependencies: [],
    allowed_paths: ['tests'],
    exclusive_paths: [],
    lease_holder: null,
    lease_expires_at: null,
    terminal_outcome: null,
    run_id: null,
    created_at: '2026-08-13T12:00:00Z',
    updated_at: '2026-08-13T12:00:00Z',
    ...overrides,
  };
}

function marco(overrides: Partial<CompanyEmployeeRecord> = {}): CompanyEmployeeRecord {
  return {
    employee_id: 'employee-marco',
    workspace_id: 'workspace_dashpro',
    name: 'Marco',
    role: 'backend',
    role_label: 'Backend',
    schedule: 'continuous',
    schedule_label: 'Continuous',
    status: 'idle',
    owns: 'Backend APIs',
    enabled: true,
    primary: false,
    last_outcome: 'failed',
    last_outcome_detail:
      'Lane B finalization failed: acceptance_evidence did not pass (Gate 6)',
    last_run_id: 'run_failed_verify',
    active_run_id: 'run_failed_verify',
    ...overrides,
  };
}

describe('verification-handoff', () => {
  it('detects verification tasks by goal prefix', () => {
    expect(
      taskIsVerificationHandoff(
        task('Verification after Marco (backend): run scoped verify commands'),
      ),
    ).toBe(true);
    expect(taskIsVerificationHandoff(task('Fix login redirect'))).toBe(false);
  });

  it('labels verification handoffs Run verification', () => {
    expect(
      verificationHandoffActionLabel(
        task('Verification after Marco (backend): npm test'),
      ),
    ).toBe('Run verification');
    expect(verificationHandoffActionLabel(task('Lead: advance plan'))).toBe('Start now');
  });

  it('resolves verification retry from gate 6 failure even with stale task snapshot', () => {
    expect(
      employeeLooksLikeVerificationRetry(
        marco(),
        [],
        [{ run_id: 'run_failed_verify', task_id: 'task_verify_failed' }],
      ),
    ).toBe(true);
    expect(
      resolveOperatorStartAction({
        employee: marco(),
        tasks: [],
        runs: [{ run_id: 'run_failed_verify', task_id: 'task_verify_failed' }],
      }),
    ).toEqual({
      taskId: 'task_verify_failed',
      task: null,
      label: 'Run verification',
    });
  });

  it('finds leased verification tickets for the employee role', () => {
    const verifyTask = task('Verification after Marco (backend): npm test', {
      task_id: 'task_verify',
      status: 'leased',
      run_id: 'run_failed_verify',
    });
    expect(
      resolveOperatorStartAction({
        employee: marco({ last_outcome_detail: null, last_outcome: null }),
        tasks: [verifyTask],
      }),
    ).toEqual({
      taskId: 'task_verify',
      task: verifyTask,
      label: 'Run verification',
    });
  });

  it('prefers gate 6 verification retry over a stale implementation handoff', () => {
    const implementationHandoff = task('Fix DashPro APIs', {
      task_id: 'task_impl',
      status: 'open',
    });
    expect(
      resolveOperatorStartAction({
        employee: marco(),
        tasks: [implementationHandoff],
        runs: [{ run_id: 'run_failed_verify', task_id: 'task_verify_failed' }],
        handoffTaskId: 'task_impl',
      }),
    ).toEqual({
      taskId: 'task_verify_failed',
      task: null,
      label: 'Run verification',
    });
    expect(
      operatorStartActionLabel({
        employee: marco(),
        task: implementationHandoff,
        tasks: [implementationHandoff],
        runs: [{ run_id: 'run_failed_verify', task_id: 'task_verify_failed' }],
      }),
    ).toBe('Run verification');
  });
});
