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

  it('parses handoff and open-source actions', () => {
    expect(
      parseChatUiAction({
        type: 'handoff_ide',
        signal_id: 'signal_123',
        target_workspace_id: 'workspace_dashpro',
        task: 'Investigate signal',
      }),
    ).toEqual({
      type: 'handoff_ide',
      signal_id: 'signal_123',
      target_workspace_id: 'workspace_dashpro',
      task: 'Investigate signal',
    });
    expect(
      parseChatUiAction({
        type: 'open_source',
        workspace_id: 'workspace_dashpro',
        open_file_path: 'src/app.ts',
      }),
    ).toEqual({
      type: 'open_source',
      workspace_id: 'workspace_dashpro',
      open_file_path: 'src/app.ts',
    });
  });
  it('parses move_voice_orb actions', () => {
    expect(parseChatUiAction({ type: 'move_voice_orb', dock: 'bottom-left' })).toEqual({
      type: 'move_voice_orb',
      dock: 'bottom-left',
    });
    expect(parseChatUiAction({ type: 'move_voice_orb', mode: 'smart_dodge' })).toEqual({
      type: 'move_voice_orb',
      mode: 'smart_dodge',
    });
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

  it('hands off a signal to the IDE', () => {
    const handoffSignalToIde = vi.fn().mockResolvedValue(undefined);

    applyChatUiAction(
      { setCurrentWorkspace: vi.fn(), openWorkspaceFile: vi.fn(), handoffSignalToIde },
      {
        type: 'handoff_ide',
        signal_id: 'signal_123',
        target_workspace_id: 'workspace_dashpro',
        task: 'Investigate signal',
      },
    );

    expect(handoffSignalToIde).toHaveBeenCalledWith({
      signal_id: 'signal_123',
      workspace_id: 'workspace_dashpro',
      task: 'Investigate signal',
      title: 'Investigate signal',
      summary: 'Investigate signal',
    }, { autoSubmit: true });
  });

  it('moves the voice orb dock and smart-dodges on command', () => {
    const setVoiceOrbDock = vi.fn();
    const requestVoiceOrbSmartDodge = vi.fn();

    applyChatUiAction(
      {
        setCurrentWorkspace: vi.fn(),
        openWorkspaceFile: vi.fn(),
        setVoiceOrbDock,
        requestVoiceOrbSmartDodge,
      },
      { type: 'move_voice_orb', dock: 'bottom-left' },
    );
    expect(setVoiceOrbDock).toHaveBeenCalledWith('bottom-left');

    applyChatUiAction(
      {
        setCurrentWorkspace: vi.fn(),
        openWorkspaceFile: vi.fn(),
        setVoiceOrbDock,
        requestVoiceOrbSmartDodge,
      },
      { type: 'move_voice_orb', mode: 'smart_dodge' },
    );
    expect(requestVoiceOrbSmartDodge).toHaveBeenCalledWith({ force: true });
  });
});
