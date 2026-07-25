import type { Ref } from 'vue';

import type { IdeComposerActivity } from '../../../lib/agent-dock-activity-view';
import {
  defaultWorkspaceStreamUi,
  shouldSyncThreadStreamGlobals,
  workspaceStreamGlobalsFromState,
  type WorkspaceStreamUiState,
} from '../../../lib/workspace-stream-ui';

interface CreateWorkspaceStreamUiSliceInput {
  /** Active IDE conversation thread — globals follow this thread only. */
  activeIdeThreadId: Ref<string | null>;
  /** Stream UI keyed by thread_id (not workspace_id). */
  workspaceStreamUiById: Ref<Record<string, WorkspaceStreamUiState>>;
  agentStreamActive: Ref<boolean>;
  agentStreamMessageId: Ref<string | null>;
  ideComposerActivity: Ref<IdeComposerActivity | null>;
  ideAgentRunId: Ref<string | null>;
}

export function createWorkspaceStreamUiSlice(input: CreateWorkspaceStreamUiSliceInput) {
  function getWorkspaceStreamUi(threadId: string): WorkspaceStreamUiState {
    return input.workspaceStreamUiById.value[threadId] ?? defaultWorkspaceStreamUi();
  }

  function applyWorkspaceStreamUiToGlobals(threadId: string): void {
    if (!shouldSyncThreadStreamGlobals(input.activeIdeThreadId.value, threadId)) {
      return;
    }
    const next = getWorkspaceStreamUi(threadId);
    const globals = workspaceStreamGlobalsFromState(next);
    input.agentStreamActive.value = globals.agentStreamActive;
    input.agentStreamMessageId.value = globals.agentStreamMessageId;
    input.ideComposerActivity.value = globals.ideComposerActivity as IdeComposerActivity | null;
    input.ideAgentRunId.value = globals.ideAgentRunId;
  }

  function setWorkspaceStreamUi(
    threadId: string,
    partial: Partial<WorkspaceStreamUiState>,
  ): void {
    input.workspaceStreamUiById.value = {
      ...input.workspaceStreamUiById.value,
      [threadId]: {
        ...getWorkspaceStreamUi(threadId),
        ...partial,
      },
    };
    applyWorkspaceStreamUiToGlobals(threadId);
  }

  return {
    getWorkspaceStreamUi,
    applyWorkspaceStreamUiToGlobals,
    setWorkspaceStreamUi,
  };
}
