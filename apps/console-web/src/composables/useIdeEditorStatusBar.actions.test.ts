import { describe, expect, it, vi } from 'vitest';

vi.mock('../lib/agent-dock-composer-focus', () => ({
  focusAgentDockComposerInput: vi.fn(),
}));

import {
  ensureWatchConnectorsLoaded,
  handleIdeLayoutShortcutAction,
  handleIdeQuickGuideAction,
  openEmployeeShiftRetry,
  openIdeSearch,
  openIdeSourceControl,
  openWatchConnectors,
} from './useIdeEditorStatusBar';
import { mockShell } from './useIdeEditorStatusBar.fixture';

describe('ensureWatchConnectorsLoaded', () => {
  it('loads connectors when the snapshot is still idle', () => {
    const shell = mockShell({ connectorsLoadState: 'idle' });

    ensureWatchConnectorsLoaded(shell as never);

    expect(shell.loadConnectors).toHaveBeenCalledOnce();
    expect(shell.loadConnectors).toHaveBeenCalledWith();
  });

  it('background-refreshes when a cached snapshot exists', () => {
    const shell = mockShell({ connectorsLoadState: 'loaded' });

    ensureWatchConnectorsLoaded(shell as never);

    expect(shell.loadConnectors).toHaveBeenCalledOnce();
    expect(shell.loadConnectors).toHaveBeenCalledWith({ background: true });
  });

  it('does not reload while a foreground fetch is in flight', () => {
    const shell = mockShell({ connectorsLoadState: 'loading' });

    ensureWatchConnectorsLoaded(shell as never);

    expect(shell.loadConnectors).not.toHaveBeenCalled();
  });
});

describe('openIdeSourceControl', () => {
  it('focuses the Source Control sidebar', () => {
    const shell = mockShell();

    openIdeSourceControl(shell as never);

    expect(shell.focusIdeSidebarView).toHaveBeenCalledOnce();
    expect(shell.focusIdeSidebarView).toHaveBeenCalledWith('git');
  });
});

describe('openIdeSearch', () => {
  it('loads workspace files when needed and focuses the Search sidebar', () => {
    const shell = mockShell({ workspaceFilesLoadState: 'idle' });

    openIdeSearch(shell as never);

    expect(shell.loadWorkspaceFiles).toHaveBeenCalledOnce();
    expect(shell.focusIdeSidebarView).toHaveBeenCalledOnce();
    expect(shell.focusIdeSidebarView).toHaveBeenCalledWith('search');
  });

  it('skips reload when the file index is already loaded', () => {
    const shell = mockShell({ workspaceFilesLoadState: 'loaded' });

    openIdeSearch(shell as never);

    expect(shell.loadWorkspaceFiles).not.toHaveBeenCalled();
    expect(shell.focusIdeSidebarView).toHaveBeenCalledOnce();
    expect(shell.focusIdeSidebarView).toHaveBeenCalledWith('search');
  });
});

describe('openWatchConnectors', () => {
  it('background-refreshes cached connectors and focuses the watch connectors surface', () => {
    const shell = mockShell();

    openWatchConnectors(shell as never);

    expect(shell.loadConnectors).toHaveBeenCalledOnce();
    expect(shell.loadConnectors).toHaveBeenCalledWith({ background: true });
    expect(shell.focusWatchConnectors).toHaveBeenCalledOnce();
  });

  it('loads connectors when the snapshot is still idle', () => {
    const shell = mockShell({ connectorsLoadState: 'idle' });

    openWatchConnectors(shell as never);

    expect(shell.loadConnectors).toHaveBeenCalledOnce();
    expect(shell.loadConnectors).toHaveBeenCalledWith();
    expect(shell.focusWatchConnectors).toHaveBeenCalledOnce();
  });
});

describe('openEmployeeShiftRetry', () => {
  it('opens the agent dock, seeds a retry draft, and submits the agent run', async () => {
    const employee = {
      employee_id: 'e1',
      workspace_id: 'workspace_demo',
      name: 'Jules',
      role: 'frontend',
      role_label: 'UI/UX',
      schedule: 'continuous',
      schedule_label: 'Continuous',
      status: 'idle',
      owns: 'console UI/UX',
      enabled: true,
      primary: false,
      last_outcome: 'failed',
      last_outcome_detail: 'vitest assertion failed',
    };
    const shell = mockShell({ activeIdeEmployeeRecord: employee });
    const showAgentDock = vi.fn();

    await openEmployeeShiftRetry({ shell: shell as never, showAgentDock });

    expect(showAgentDock).toHaveBeenCalledOnce();
    expect(shell.openOrFocusEmployeeIdeThread).toHaveBeenCalledOnce();
    expect(shell.setAgentExecutionAccess).toHaveBeenCalledWith('full');
    expect(shell.openIdeComposerWithDraft).toHaveBeenCalledOnce();
    const draft = vi.mocked(shell.openIdeComposerWithDraft).mock.calls[0]?.[0] ?? '';
    expect(draft).toContain('console UI/UX');
    expect(draft).toMatch(/my last continuous shift/i);
    expect(draft).toContain('vitest assertion failed');
    // First-person/persona voice steering is injected server-side (employee_persona_prompt.py)
    // for every employee dispatch — it must not be duplicated into this persisted message.
    expect(draft.toLowerCase()).not.toContain('first person');
    expect(shell.submitIdeComposer).toHaveBeenCalledWith('agent', {
      contentOverride: draft,
    });
  });
});


describe('handleIdeLayoutShortcutAction', () => {
  it('opens Search through the shared sidebar entry point and retries failed file loads', () => {
    const shell = mockShell({ workspaceFilesLoadState: 'error' });

    handleIdeLayoutShortcutAction('open-search', shell as never);

    expect(shell.loadWorkspaceFiles).toHaveBeenCalledOnce();
    expect(shell.focusIdeSidebarView).toHaveBeenCalledOnce();
    expect(shell.focusIdeSidebarView).toHaveBeenCalledWith('search');
  });

  it('opens Source Control through the shared sidebar entry point', () => {
    const shell = mockShell();

    handleIdeLayoutShortcutAction('open-source-control', shell as never);

    expect(shell.focusIdeSidebarView).toHaveBeenCalledOnce();
    expect(shell.focusIdeSidebarView).toHaveBeenCalledWith('git');
  });

  it('toggles the terminal panel for Ctrl/Cmd+J', () => {
    const shell = mockShell();

    handleIdeLayoutShortcutAction('toggle-terminal', shell as never);

    expect(shell.toggleIdeTerminalPanel).toHaveBeenCalledOnce();
  });
});

describe('handleIdeQuickGuideAction', () => {
  it('expands the agent dock', () => {
    const showAgentDock = vi.fn();
    const showTerminalPanel = vi.fn();

    handleIdeQuickGuideAction('expand-agent-dock', {
      shell: mockShell() as never,
      showAgentDock,
      showTerminalPanel,
    });

    expect(showAgentDock).toHaveBeenCalledOnce();
    expect(showTerminalPanel).not.toHaveBeenCalled();
  });

  it('opens watch connectors', () => {
    const shell = mockShell();
    const showAgentDock = vi.fn();
    const showTerminalPanel = vi.fn();

    handleIdeQuickGuideAction('open-connectors', {
      shell: shell as never,
      showAgentDock,
      showTerminalPanel,
    });

    expect(shell.loadConnectors).toHaveBeenCalledOnce();
    expect(shell.loadConnectors).toHaveBeenCalledWith({ background: true });
    expect(shell.focusWatchConnectors).toHaveBeenCalledOnce();
    expect(showAgentDock).not.toHaveBeenCalled();
  });

  it('shows the terminal panel for show-terminal actions', () => {
    const showAgentDock = vi.fn();
    const showTerminalPanel = vi.fn();

    handleIdeQuickGuideAction('show-terminal', {
      shell: mockShell() as never,
      showAgentDock,
      showTerminalPanel,
    });

    expect(showTerminalPanel).toHaveBeenCalledOnce();
    expect(showAgentDock).not.toHaveBeenCalled();
  });

  it('retries the active teammate shift from the quick guide', async () => {
    const employee = {
      employee_id: 'e1',
      workspace_id: 'workspace_demo',
      name: 'Jules',
      role: 'frontend',
      role_label: 'UI/UX',
      schedule: 'continuous',
      schedule_label: 'Continuous',
      status: 'idle',
      owns: 'console UI/UX',
      enabled: true,
      primary: false,
      last_outcome: 'failed',
      last_outcome_detail: 'timeout',
    };
    const shell = mockShell({ activeIdeEmployeeRecord: employee });
    const showAgentDock = vi.fn();
    const showTerminalPanel = vi.fn();

    handleIdeQuickGuideAction('retry-employee-shift', {
      shell: shell as never,
      showAgentDock,
      showTerminalPanel,
    });
    await vi.waitFor(() => {
      expect(shell.submitIdeComposer).toHaveBeenCalledWith(
        'agent',
        expect.objectContaining({
          contentOverride: expect.stringContaining('timeout'),
        }),
      );
    });

    expect(showAgentDock).toHaveBeenCalledOnce();
    expect(shell.openIdeComposerWithDraft).toHaveBeenCalledOnce();
    expect(showTerminalPanel).not.toHaveBeenCalled();
  });

  it('opens the Team sidebar from the quick guide', () => {
    const shell = mockShell();
    const showAgentDock = vi.fn();
    const showTerminalPanel = vi.fn();

    handleIdeQuickGuideAction('open-team', {
      shell: shell as never,
      showAgentDock,
      showTerminalPanel,
    });

    expect(shell.focusIdeSidebarView).toHaveBeenCalledOnce();
    expect(shell.focusIdeSidebarView).toHaveBeenCalledWith('team');
    expect(showAgentDock).not.toHaveBeenCalled();
    expect(showTerminalPanel).not.toHaveBeenCalled();
  });

  it('opens the Source Control sidebar from the quick guide', () => {
    const shell = mockShell();
    const showAgentDock = vi.fn();
    const showTerminalPanel = vi.fn();

    handleIdeQuickGuideAction('open-source-control', {
      shell: shell as never,
      showAgentDock,
      showTerminalPanel,
    });

    expect(shell.focusIdeSidebarView).toHaveBeenCalledOnce();
    expect(shell.focusIdeSidebarView).toHaveBeenCalledWith('git');
    expect(showAgentDock).not.toHaveBeenCalled();
    expect(showTerminalPanel).not.toHaveBeenCalled();
  });

  it('opens the Search sidebar from the quick guide', () => {
    const shell = mockShell();
    const showAgentDock = vi.fn();
    const showTerminalPanel = vi.fn();

    handleIdeQuickGuideAction('open-search', {
      shell: shell as never,
      showAgentDock,
      showTerminalPanel,
    });

    expect(shell.focusIdeSidebarView).toHaveBeenCalledOnce();
    expect(shell.focusIdeSidebarView).toHaveBeenCalledWith('search');
    expect(showAgentDock).not.toHaveBeenCalled();
    expect(showTerminalPanel).not.toHaveBeenCalled();
  });
});
