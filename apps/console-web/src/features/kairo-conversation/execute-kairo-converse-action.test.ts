import { describe, expect, it, vi } from 'vitest';

import { executeKairoConverseAction } from './execute-kairo-converse-action';

describe('executeKairoConverseAction lead_fan_out', () => {
  it('switches workspace, refreshes tasks, and opens the Task Board', async () => {
    const shell = {
      layoutMode: 'operator',
      setCurrentWorkspace: vi.fn(),
      loadWorkspaceTasks: vi.fn(async () => undefined),
      setLayoutMode: vi.fn(),
      focusOperatorTaskBoard: vi.fn(),
      routeTaskToEmployee: vi.fn(),
    };

    await executeKairoConverseAction(shell as never, {
      type: 'lead_fan_out',
      target_workspace_id: 'workspace_dashpro',
      task: 'push canary + dashboard fixes',
      mode: 'decompose',
      tasks: [{ task_id: 't1' }],
      runs: [],
    });

    expect(shell.setCurrentWorkspace).toHaveBeenCalledWith('workspace_dashpro');
    expect(shell.loadWorkspaceTasks).toHaveBeenCalledWith('workspace_dashpro');
    expect(shell.setLayoutMode).toHaveBeenCalledWith('ide');
    expect(shell.focusOperatorTaskBoard).toHaveBeenCalledTimes(1);
  });
});
