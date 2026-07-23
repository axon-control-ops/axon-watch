import type { IdeComposerActivity } from './agent-dock-activity-view';

export type WorkspaceStreamUiState = {
  active: boolean;
  messageId: string | null;
  activity: IdeComposerActivity | null;
  ideAgentRunId: string | null;
};

export function defaultWorkspaceStreamUi(): WorkspaceStreamUiState {
  return {
    active: false,
    messageId: null,
    activity: null,
    ideAgentRunId: null,
  };
}

/** @deprecated Prefer shouldSyncThreadStreamGlobals — kept for older call sites. */
export function shouldSyncWorkspaceStreamGlobals(
  currentWorkspaceId: string | null | undefined,
  eventWorkspaceId: string,
): boolean {
  return Boolean(currentWorkspaceId && currentWorkspaceId === eventWorkspaceId);
}

/** Sync composer/stop globals only for the IDE thread the operator is viewing. */
export function shouldSyncThreadStreamGlobals(
  currentThreadId: string | null | undefined,
  eventThreadId: string,
): boolean {
  return Boolean(currentThreadId && currentThreadId === eventThreadId);
}

export function workspaceStreamGlobalsFromState(
  state: WorkspaceStreamUiState,
): {
  agentStreamActive: boolean;
  agentStreamMessageId: string | null;
  ideComposerActivity: IdeComposerActivity | null;
  ideAgentRunId: string | null;
} {
  return {
    agentStreamActive: state.active,
    agentStreamMessageId: state.messageId,
    ideComposerActivity: state.activity,
    ideAgentRunId: state.ideAgentRunId,
  };
}

/** Thread ids with an active IDE chat stream (for busy chrome on background tabs). */
export function streamingThreadIdsFromUiMap(
  streamUiByThreadId: Record<string, WorkspaceStreamUiState> | null | undefined,
): string[] {
  if (!streamUiByThreadId) {
    return [];
  }
  return Object.entries(streamUiByThreadId)
    .filter(([, state]) => state.active)
    .map(([threadId]) => threadId);
}
