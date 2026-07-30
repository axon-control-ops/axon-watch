import type { TaskBoardRow } from '../../../lib/operator-task-board-view';
import { resolveTaskBoardStartTarget } from '../../../lib/operator-task-board-start-route';
import { useShellStore } from '../../../stores/shell';

type StartedTask = {
  task: { owner_role?: string | null; task_id: string };
  threadId: string | null;
};

export function useOperatorTaskBoardRouting() {
  const shell = useShellStore();

  async function openStartedTaskOwner(
    started: StartedTask,
    workspaceId: string,
  ): Promise<void> {
    if (shell.currentWorkspace?.workspace_id !== workspaceId) {
      return;
    }
    const target = resolveTaskBoardStartTarget({
      ownerRole: started.task.owner_role,
      threadId: started.threadId,
      roster: shell.companyEmployeesForCurrentWorkspace,
    });
    if (target.employee) {
      if (target.threadId) {
        await shell.selectIdeThread(target.threadId, { forceRefresh: true });
        shell.openIdeComposer({ keepActivityView: true });
      } else {
        await shell.openOrFocusEmployeeIdeThread(target.employee, { forceRefresh: true });
      }
      if (shell.currentWorkspace?.workspace_id !== workspaceId) {
        return;
      }
      shell.setLayoutMode('ide');
      return;
    }
    shell.commandMutationError = `No enabled teammate is staffed for role "${target.ownerRole}". Assign or enable that role in Fleet.`;
  }

  async function startTaskAndOpenOwner(
    taskId: string,
    refreshScheduler: () => Promise<void>,
    selectTask: (taskId: string) => void,
  ): Promise<void> {
    const workspaceId = shell.currentWorkspace?.workspace_id?.trim();
    if (!workspaceId) {
      return;
    }
    const started = await shell.startCurrentWorkspaceTask(taskId);
    if (!started || shell.currentWorkspace?.workspace_id !== workspaceId) {
      shell.commandMutationError =
        shell.workspaceTasksError || 'Could not start the selected handoff task.';
      return;
    }
    const phase = (started.runPhase ?? '').trim().toLowerCase();
    if (!started.runId || !phase || phase === 'queued') {
      shell.commandMutationError =
        'Handoff is still queued; worker dispatch did not start. Check capacity and try again.';
      return;
    }
    selectTask(started.task.task_id);
    await Promise.all([
      refreshScheduler(),
      shell.loadCompanyEmployees(workspaceId),
      shell.loadRuns({ sync: false }),
    ]);
    if (shell.currentWorkspace?.workspace_id === workspaceId) {
      await openStartedTaskOwner(started, workspaceId);
    }
  }

  async function openSpecialist(row: TaskBoardRow): Promise<void> {
    const target = resolveTaskBoardStartTarget({
      ownerRole: row.ownerRole === 'unassigned' ? '' : row.ownerRole,
      roster: shell.companyEmployeesForCurrentWorkspace,
    });
    if (target.employee) {
      await shell.openOrFocusEmployeeIdeThread(target.employee);
      shell.setLayoutMode('ide');
      return;
    }
    shell.commandMutationError = `No teammate staffed for role "${target.ownerRole || row.ownerRole}" — assign the role in Fleet.`;
  }

  return { openSpecialist, startTaskAndOpenOwner };
}
