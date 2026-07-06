import { describe, expect, it, vi } from 'vitest';

import { applyChatUiAction, parseChatUiAction } from './chat-ui-action';

describe('parseChatUiAction', () => {
  it('parses switch_workspace actions', () => {
    expect(
      parseChatUiAction({
        type: 'switch_workspace',
        workspace_id: 'workspace_dashpro',
        open_file_path: 'README.md',
      }),
    ).toEqual({
      type: 'switch_workspace',
      workspace_id: 'workspace_dashpro',
      open_file_path: 'README.md',
    });
  });

  it('returns null for unknown actions', () => {
    expect(parseChatUiAction({ type: 'noop' })).toBeNull();
    expect(parseChatUiAction(null)).toBeNull();
  });
});

describe('applyChatUiAction', () => {
  it('switches workspace and opens a file', () => {
    const setCurrentWorkspace = vi.fn();
    const openWorkspaceFile = vi.fn().mockResolvedValue(undefined);

    applyChatUiAction(
      { setCurrentWorkspace, openWorkspaceFile },
      {
        type: 'switch_workspace',
        workspace_id: 'workspace_dashpro',
        open_file_path: 'README.md',
      },
    );

    expect(setCurrentWorkspace).toHaveBeenCalledWith('workspace_dashpro');
    expect(openWorkspaceFile).toHaveBeenCalledWith('README.md');
  });
});
