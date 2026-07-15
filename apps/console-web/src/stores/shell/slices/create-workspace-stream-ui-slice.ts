import type { Ref } from 'vue';

import type { IdeComposerActivity } from '../../../lib/agent-dock-activity-view';
import {
  defaultWorkspaceStreamUi,
  shouldSyncWorkspaceStreamGlobals,
  workspaceStreamGlobalsFromState,
  type WorkspaceStreamUiState,
} from '../../../lib/workspace-stream-ui';

interface CreateWorkspaceStreamUiSliceInput {
  currentWorkspace: Ref<{ workspace_id: string } | null>;
  workspaceStreamUiById: Ref<Record<string, WorkspaceStreamUiState>>;
  agentStreamActive: Ref<boolean>;
  agentStreamMessageId: Ref<string | null>;
  ideComposerActivity: Ref<IdeComposerActivity | null>;
  ideAgentRunId: Ref<string | null>;
}

export function createWorkspaceStreamUiSlice(input: CreateWorkspaceStreamUiSliceInput) {
  function getWorkspaceStreamUi(workspaceId: string): WorkspaceStreamUiState {
    return input.workspaceStreamUiById.value[workspaceId] ?? defaultWorkspaceStreamUi();
  }

  function applyWorkspaceStreamUiToGlobals(workspaceId: string): void {
    if (!shouldSyncWorkspaceStreamGlobals(input.currentWorkspace.value?.workspace_id, workspaceId)) {
      return;
    }
    const next = getWorkspaceStreamUi(workspaceId);
    const globals = workspaceStreamGlobalsFromState(next);
    input.agentStreamActive.value = globals.agentStreamActive;
    input.agentStreamMessageId.value = globals.agentStreamMessageId;
    input.ideComposerActivity.value = globals.ideComposerActivity as IdeComposerActivity | null;
    input.ideAgentRunId.value = globals.ideAgentRunId;
  }

  function setWorkspaceStreamUi(
    workspaceId: string,
    partial: Partial<WorkspaceStreamUiState>,
  ): void {
    input.workspaceStreamUiById.value = {
      ...input.workspaceStreamUiById.value,
      [workspaceId]: {
        ...getWorkspaceStreamUi(workspaceId),
        ...partial,
      },
    };
    applyWorkspaceStreamUiToGlobals(workspaceId);
  }

  return {
    getWorkspaceStreamUi,
    applyWorkspaceStreamUiToGlobals,
    setWorkspaceStreamUi,
  };
}
