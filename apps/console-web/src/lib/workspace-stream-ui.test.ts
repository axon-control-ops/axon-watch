import { describe, expect, it } from 'vitest';
import {
  defaultWorkspaceStreamUi,
  shouldSyncWorkspaceStreamGlobals,
  workspaceStreamGlobalsFromState,
} from './workspace-stream-ui';

describe('workspace-stream-ui', () => {
  it('syncs globals only for the visible workspace', () => {
    expect(shouldSyncWorkspaceStreamGlobals('workspace_a', 'workspace_a')).toBe(true);
    expect(shouldSyncWorkspaceStreamGlobals('workspace_a', 'workspace_b')).toBe(false);
    expect(shouldSyncWorkspaceStreamGlobals(null, 'workspace_a')).toBe(false);
  });

  it('maps stream ui state to global fields', () => {
    const state = {
      ...defaultWorkspaceStreamUi(),
      active: true,
      messageId: 'msg_1',
      ideAgentRunId: 'run_1',
    };
    expect(workspaceStreamGlobalsFromState(state)).toEqual({
      agentStreamActive: true,
      agentStreamMessageId: 'msg_1',
      ideComposerActivity: null,
      ideAgentRunId: 'run_1',
    });
  });
});
