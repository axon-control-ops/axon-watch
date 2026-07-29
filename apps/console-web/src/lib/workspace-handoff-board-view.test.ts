import { describe, expect, it } from 'vitest';

import {
  incomingHandoffHeadline,
  mapWorkspaceHandoffRows,
} from './workspace-handoff-board-view';

describe('workspace-handoff-board-view', () => {
  it('maps incoming and outgoing open handoffs for the focused workspace', () => {
    const rows = mapWorkspaceHandoffRows(
      [
        {
          handoff_id: 'handoff-in',
          source_workspace_id: 'workspace_smoke',
          target_workspace_id: 'workspace_alpha',
          task: 'Review bootstrap',
          status: 'routed',
          target_task_id: 'task-1',
          routed_role: 'backend',
        },
        {
          handoff_id: 'handoff-out',
          source_workspace_id: 'workspace_alpha',
          target_workspace_id: 'workspace_dashpro',
          task: 'Ship patch',
          status: 'recorded',
        },
        {
          handoff_id: 'handoff-other',
          source_workspace_id: 'workspace_smoke',
          target_workspace_id: 'workspace_dashpro',
          task: 'Ignore me',
          status: 'routed',
        },
      ],
      'workspace_alpha',
    );
    expect(rows).toEqual([
      {
        handoffId: 'handoff-in',
        sourceWorkspaceId: 'workspace_smoke',
        targetWorkspaceId: 'workspace_alpha',
        task: 'Review bootstrap',
        status: 'routed',
        targetTaskId: 'task-1',
        routedRole: 'backend',
        direction: 'incoming',
      },
      {
        handoffId: 'handoff-out',
        sourceWorkspaceId: 'workspace_alpha',
        targetWorkspaceId: 'workspace_dashpro',
        task: 'Ship patch',
        status: 'recorded',
        targetTaskId: null,
        routedRole: '',
        direction: 'outgoing',
      },
    ]);
  });

  it('hides handoffs whose target task is already terminal', () => {
    const rows = mapWorkspaceHandoffRows(
      [
        {
          handoff_id: 'handoff-done',
          source_workspace_id: 'workspace_smoke',
          target_workspace_id: 'workspace_alpha',
          task: 'Finished work',
          status: 'routed',
          target_task_id: 'task-done',
        },
        {
          handoff_id: 'handoff-open',
          source_workspace_id: 'workspace_smoke',
          target_workspace_id: 'workspace_alpha',
          task: 'Still open',
          status: 'routed',
          target_task_id: 'task-open',
        },
      ],
      'workspace_alpha',
      {
        taskStatusById: {
          'task-done': 'completed',
          'task-open': 'open',
        },
      },
    );
    expect(rows.map((row) => row.handoffId)).toEqual(['handoff-open']);
  });

  it('builds a short headline for board chrome', () => {
    expect(
      incomingHandoffHeadline({
        handoffId: 'h1',
        sourceWorkspaceId: 'workspace_smoke',
        targetWorkspaceId: 'workspace_alpha',
        task: 'x',
        status: 'routed',
        targetTaskId: 't1',
        routedRole: 'frontend',
        direction: 'incoming',
      }),
    ).toBe('From smoke · frontend');
  });
});
