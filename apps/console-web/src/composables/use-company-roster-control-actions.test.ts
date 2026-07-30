import { ref } from 'vue';
import { describe, expect, it, vi } from 'vitest';

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
}) {
  return {
    startCurrentWorkspaceTask: vi.fn().mockResolvedValue({
      task: { task_id: 'task_handoff' },
      threadId: 'thread_soren',
      ...result,
    }),
    workspaceTasksError: null,
    loadCompanyEmployees: vi.fn().mockResolvedValue(undefined),
    loadRuns: vi.fn().mockResolvedValue(undefined),
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

  it('refreshes and opens the employee only after the target is executing', async () => {
    const shell = shellWithStart({ runId: 'run_active', runPhase: 'executing' });
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
    expect(shell.openOrFocusEmployeeIdeThread).toHaveBeenCalledWith(employee, {
      forceRefresh: true,
    });
    expect(shell.rehydrateWorkspaceIdeStreams).toHaveBeenCalledWith('workspace_dashpro');
    expect(shell.setLayoutMode).toHaveBeenCalledWith('ide');
  });
});
