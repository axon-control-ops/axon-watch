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

/** Apply per-workspace stream UI to global refs only when that workspace is visible. */
export function shouldSyncWorkspaceStreamGlobals(
  currentWorkspaceId: string | null | undefined,
  eventWorkspaceId: string,
): boolean {
  return Boolean(currentWorkspaceId && currentWorkspaceId === eventWorkspaceId);
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
