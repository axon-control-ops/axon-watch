import { ref } from 'vue';
import { describe, expect, it, vi } from 'vitest';

import type { WorkspaceTaskRecord } from '../api/tasks-api';
import type { CompanyEmployeeRecord } from '../contracts/canonical';
import { useCompanyRosterControlActions } from './use-company-roster-control-actions';

const employee: CompanyEmployeeRecord = {
  employee_id: 'employee-soren',
  workspace_id: 'workspace_dashpro',
  name: 'Soren',
  role: 'integrations',
  role_label: 'Integrations',
  schedule: 'continuous',
  schedule_label: 'Continuous',
  status: 'assigned',
  owns: 'OTA',
  enabled: true,
  primary: false,
};

function shellWithStart(result: {
  runId: string | null;
  runPhase: string | null;
  threadId?: string | null;
}) {
  const threadId = result.threadId === undefined ? 'thread_soren' : result.threadId;
  return {
    startCurrentWorkspaceTask: vi.fn().mockResolvedValue({
      task: { task_id: 'task_handoff' },
      threadId,
      runId: result.runId,
      runPhase: result.runPhase,
    }),
    workspaceTasksError: null,
    workspaceTasksForCurrentWorkspace: [] as WorkspaceTaskRecord[],
    operatorPresenceSettings: { autonomy_mode: 'manual' },
    runs: [],
    loadWorkspaceTasks: vi.fn().mockResolvedValue(undefined),
    loadCompanyEmployees: vi.fn().mockResolvedValue(undefined),
    loadRuns: vi.fn().mockResolvedValue(undefined),
    selectIdeThread: vi.fn().mockResolvedValue(undefined),
    openIdeComposer: vi.fn(),
    openOrFocusEmployeeIdeThread: vi.fn().mockResolvedValue('thread_soren'),
    rehydrateWorkspaceIdeStreams: vi.fn().mockResolvedValue(undefined),
    setLayoutMode: vi.fn(),
  };
}

describe('useCompanyRosterControlActions', () => {
  it('does not claim success when Start leaves the handoff queued', async () => {
    const shell = shellWithStart({ runId: 'run_queued', runPhase: 'queued' });
    const loadCompany = vi.fn().mockResolvedValue(undefined);
    const actions = useCompanyRosterControlActions({
      shell: shell as never,
      currentWorkspaceId: ref('workspace_dashpro'),
      loadCompany,
    });

    await actions.onControlAction(employee, {
      id: 'start_now',
      label: 'Start now',
      kind: 'control',
      control: 'start_now',
      taskId: 'task_handoff',
    });

    expect(actions.controlError.value).toContain('still queued');
    expect(loadCompany).not.toHaveBeenCalled();
    expect(shell.setLayoutMode).not.toHaveBeenCalled();
  });

  it('treats starting as dispatch success and opens the returned IDE thread', async () => {
    const shell = shellWithStart({ runId: 'run_active', runPhase: 'starting' });
    const loadCompany = vi.fn().mockResolvedValue(undefined);
    const actions = useCompanyRosterControlActions({
      shell: shell as never,
      currentWorkspaceId: ref('workspace_dashpro'),
      loadCompany,
    });

    await actions.onControlAction(employee, {
      id: 'start_now',
      label: 'Start now',
      kind: 'control',
      control: 'start_now',
      taskId: 'task_handoff',
    });

    expect(actions.controlError.value).toBeNull();
    expect(loadCompany).toHaveBeenCalledOnce();
    expect(shell.loadCompanyEmployees).toHaveBeenCalledWith('workspace_dashpro');
    expect(shell.loadRuns).toHaveBeenCalledWith({ sync: false });
    expect(shell.selectIdeThread).toHaveBeenCalledWith('thread_soren', {
      forceRefresh: true,
    });
    expect(shell.openIdeComposer).toHaveBeenCalledWith({ keepActivityView: true });
    expect(shell.openOrFocusEmployeeIdeThread).not.toHaveBeenCalled();
    expect(shell.rehydrateWorkspaceIdeStreams).toHaveBeenCalledWith('workspace_dashpro');
    expect(shell.setLayoutMode).toHaveBeenCalledWith('ide');
  });

  it('falls back to employee IDE focus when Start returns no thread', async () => {
    const shell = shellWithStart({
      runId: 'run_active',
      runPhase: 'executing',
      threadId: null,
    });
    const loadCompany = vi.fn().mockResolvedValue(undefined);
    const actions = useCompanyRosterControlActions({
      shell: shell as never,
      currentWorkspaceId: ref('workspace_dashpro'),
      loadCompany,
    });

    await actions.onControlAction(employee, {
      id: 'start_now',
      label: 'Start now',
      kind: 'control',
      control: 'start_now',
      taskId: 'task_handoff',
    });

    expect(actions.controlError.value).toBeNull();
    expect(shell.openOrFocusEmployeeIdeThread).toHaveBeenCalledWith(employee, {
      forceRefresh: true,
    });
    expect(shell.setLayoutMode).toHaveBeenCalledWith('ide');
  });

  it('surfaces an error when Start now has no bound task', async () => {
    const shell = shellWithStart({ runId: 'run_active', runPhase: 'executing' });
    const actions = useCompanyRosterControlActions({
      shell: shell as never,
      currentWorkspaceId: ref('workspace_dashpro'),
      loadCompany: vi.fn(),
    });

    await actions.onControlAction(employee, {
      id: 'start_now',
      label: 'Start now',
      kind: 'control',
      control: 'start_now',
    });

    expect(actions.controlError.value).toContain('No handoff task');
    expect(shell.startCurrentWorkspaceTask).not.toHaveBeenCalled();
  });

  it('defers IDE focus for Run verification so the roster stays responsive', async () => {
    vi.useFakeTimers();
    const shell = shellWithStart({ runId: 'run_verify', runPhase: 'executing' });
    shell.workspaceTasksForCurrentWorkspace = [
      {
        task_id: 'task_verify',
        workspace_id: 'workspace_dashpro',
        goal: 'Verification after Marco (backend): run scoped verify commands — `npm test`',
        acceptance_criteria: 'Attach stdout receipts.',
        risk: 'low',
        owner_role: 'integrations',
        dependencies: [],
        status: 'open',
        lease_holder: null,
        lease_expires_at: null,
        attempt_budget: 3,
        attempts_used: 0,
        terminal_outcome: null,
        run_id: null,
        created_at: '2026-01-01T00:00:00Z',
        updated_at: '2026-01-01T00:00:00Z',
      },
    ];
    const loadCompany = vi.fn().mockResolvedValue(undefined);
    const actions = useCompanyRosterControlActions({
      shell: shell as never,
      currentWorkspaceId: ref('workspace_dashpro'),
      loadCompany,
    });

    await actions.onControlAction(employee, {
      id: 'start_now',
      label: 'Run verification',
      kind: 'control',
      control: 'start_now',
      taskId: 'task_verify',
    });

    expect(actions.controlError.value).toBeNull();
    expect(shell.setLayoutMode).not.toHaveBeenCalled();
    await vi.runAllTimersAsync();
    expect(shell.selectIdeThread).toHaveBeenCalledWith('thread_soren', {
      forceRefresh: false,
    });
    expect(shell.setLayoutMode).toHaveBeenCalledWith('ide');
    vi.useRealTimers();
  });
});
