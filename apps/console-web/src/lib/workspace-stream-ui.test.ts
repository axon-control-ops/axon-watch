import { describe, expect, it } from 'vitest';
import {
  defaultWorkspaceStreamUi,
  shouldSyncThreadStreamGlobals,
  shouldSyncWorkspaceStreamGlobals,
  streamingThreadIdsFromUiMap,
  workspaceStreamGlobalsFromState,
} from './workspace-stream-ui';

describe('workspace-stream-ui', () => {
  it('syncs globals only for the visible workspace', () => {
    expect(shouldSyncWorkspaceStreamGlobals('workspace_a', 'workspace_a')).toBe(true);
    expect(shouldSyncWorkspaceStreamGlobals('workspace_a', 'workspace_b')).toBe(false);
    expect(shouldSyncWorkspaceStreamGlobals(null, 'workspace_a')).toBe(false);
  });

  it('syncs globals only for the focused IDE thread', () => {
    expect(shouldSyncThreadStreamGlobals('thread_a', 'thread_a')).toBe(true);
    expect(shouldSyncThreadStreamGlobals('thread_a', 'thread_b')).toBe(false);
    expect(shouldSyncThreadStreamGlobals(null, 'thread_a')).toBe(false);
  });

  it('lists active streaming thread ids', () => {
    expect(
      streamingThreadIdsFromUiMap({
        thread_a: { ...defaultWorkspaceStreamUi(), active: true },
        thread_b: defaultWorkspaceStreamUi(),
        thread_c: { ...defaultWorkspaceStreamUi(), active: true },
      }),
    ).toEqual(['thread_a', 'thread_c']);
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
