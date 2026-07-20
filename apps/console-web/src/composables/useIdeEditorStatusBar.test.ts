import { describe, expect, it, vi } from 'vitest';
import { computed, ref } from 'vue';

import {
  handleIdeQuickGuideAction,
  openWatchConnectors,
  useIdeEditorStatusBar,
} from './useIdeEditorStatusBar';

vi.mock('../lib/agent-dock-composer-focus', () => ({
  focusAgentDockComposerInput: vi.fn(),
}));

function mockShell(overrides: Record<string, unknown> = {}) {
  return {
    agentDockCollapsed: true,
    pendingApprovalsCount: 0,
    agentStreamActive: false,
    primaryActiveRun: null,
    activeIdeEmployeeRecord: null,
    activeIdeEmployeeFailureLine: null,
    activeIdeEmployeeShiftInterrupted: false,
    connectorsLoadState: 'loaded',
    connectorsItems: [],
    connectorsSummary: { required_unavailable: 0 },
    runtimeSummary: { watch: { connected: true } },
    loadConnectors: vi.fn(),
    focusWatchConnectors: vi.fn(),
    openIdeComposerWithDraft: vi.fn(),
    openIdeComposer: vi.fn(),
    revealTeamRosterForActiveEmployee: vi.fn(),
    ...overrides,
  };
}

describe('useIdeEditorStatusBar', () => {
  it('builds terminal, agent, connector, and quick-guide chips from shell state', () => {
    const shell = mockShell({
      agentDockCollapsed: true,
      pendingApprovalsCount: 1,
      connectorsSummary: { required_unavailable: 2 },
    });
    const { ideEditorStatusAgentChip, ideEditorStatusConnectorChip, ideQuickGuide } =
      useIdeEditorStatusBar({
        shell: shell as never,
        workbenchLayoutMode: computed(() => 'ide'),
        terminalPanelVisible: ref(false),
        terminalReopenRunPhase: computed(() => null),
        agentDockReopenState: computed(() => ({
          streaming: false,
          pendingApprovals: 1,
          runPhase: null,
        })),
      });

    expect(ideEditorStatusAgentChip.value).toMatchObject({
      label: 'AGENT',
      showBadge: 1,
      approvals: true,
    });
    expect(ideEditorStatusConnectorChip.value).toMatchObject({
      label: '2 REQ DOWN',
    });
    expect(ideQuickGuide.value?.title).toContain('Approval waiting');
  });

  it('suppresses stale required-connector quick guide when watch is offline', () => {
    const shell = mockShell({
      agentDockCollapsed: false,
      connectorsSummary: { required_unavailable: 2 },
      runtimeSummary: { watch: { connected: false } },
    });
    const { ideEditorStatusConnectorChip, ideQuickGuide } = useIdeEditorStatusBar({
      shell: shell as never,
      workbenchLayoutMode: computed(() => 'ide'),
      terminalPanelVisible: ref(false),
      terminalReopenRunPhase: computed(() => null),
      agentDockReopenState: computed(() => ({
        streaming: false,
        pendingApprovals: 0,
        runPhase: null,
      })),
    });

    expect(ideEditorStatusConnectorChip.value).toMatchObject({
      id: 'watch-offline',
      label: 'WATCH OFFLINE',
    });
    expect(ideQuickGuide.value?.title).toContain('Watch offline');
    expect(ideQuickGuide.value?.title).not.toContain('connector down');
  });

  it('hides terminal chip when the panel is already visible', () => {
    const { ideEditorStatusTerminalChip } = useIdeEditorStatusBar({
      shell: mockShell() as never,
      workbenchLayoutMode: computed(() => 'ide'),
      terminalPanelVisible: ref(true),
      terminalReopenRunPhase: computed(() => 'executing'),
      agentDockReopenState: computed(() => ({
        streaming: false,
        pendingApprovals: 0,
        runPhase: null,
      })),
    });

    expect(ideEditorStatusTerminalChip.value).toBeNull();
  });

  it('surfaces interrupted teammate guidance through the quick guide', () => {
    const shell = mockShell({
      activeIdeEmployeeRecord: {
        employee_id: 'jules',
        name: 'Jules',
        role: 'frontend',
        role_label: 'Frontend',
        owns: 'console UI',
        enabled: true,
        status: 'idle',
        last_outcome: 'failed',
        last_outcome_detail: 'Run interrupted by control-plane restart',
      },
      activeIdeEmployeeFailureLine:
        'Last shift interrupted before it could finish — use Continue shift to pick up where you left off.',
      activeIdeEmployeeShiftInterrupted: true,
    });
    const { ideQuickGuide } = useIdeEditorStatusBar({
      shell: shell as never,
      workbenchLayoutMode: computed(() => 'ide'),
      terminalPanelVisible: ref(false),
      terminalReopenRunPhase: computed(() => null),
      agentDockReopenState: computed(() => ({
        streaming: false,
        pendingApprovals: 0,
        runPhase: null,
        employeeFailureLine: shell.activeIdeEmployeeFailureLine,
        employeeShiftInterrupted: true,
      })),
    });

    expect(ideQuickGuide.value?.tone).toBe('interrupted');
    expect(ideQuickGuide.value?.title).toContain('continue from the quick guide');
  });
});

describe('openWatchConnectors', () => {
  it('loads connectors and focuses the watch connectors surface', () => {
    const shell = mockShell();

    openWatchConnectors(shell as never);

    expect(shell.loadConnectors).toHaveBeenCalledOnce();
    expect(shell.focusWatchConnectors).toHaveBeenCalledOnce();
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

  it('opens a retry draft for the active teammate', () => {
    const shell = mockShell({
      activeIdeEmployeeRecord: {
        employee_id: 'jules',
        name: 'Jules',
        role: 'frontend',
        role_label: 'Frontend',
        owns: 'console UI',
        enabled: true,
        last_outcome_detail: 'vitest assertion failed',
      },
    });
    const showAgentDock = vi.fn();
    const showTerminalPanel = vi.fn();

    handleIdeQuickGuideAction('retry-employee-shift', {
      shell: shell as never,
      showAgentDock,
      showTerminalPanel,
    });

    expect(showAgentDock).toHaveBeenCalledOnce();
    expect(shell.openIdeComposerWithDraft).toHaveBeenCalledOnce();
    expect(String(shell.openIdeComposerWithDraft.mock.calls[0]?.[0])).toContain('Jules');
    expect(showTerminalPanel).not.toHaveBeenCalled();
  });

  it('opens receipts in ask mode when view receipts is chosen', () => {
    const shell = mockShell({
      activeIdeEmployeeRecord: {
        employee_id: 'jules',
        name: 'Jules',
        role: 'frontend',
        role_label: 'Frontend',
        owns: 'console UI',
        enabled: true,
        last_run_id: 'run-123',
        last_outcome_detail: 'vitest assertion failed',
      },
    });
    const showAgentDock = vi.fn();
    const showTerminalPanel = vi.fn();

    handleIdeQuickGuideAction('view-employee-receipts', {
      shell: shell as never,
      showAgentDock,
      showTerminalPanel,
    });

    expect(showAgentDock).toHaveBeenCalledOnce();
    expect(shell.openIdeComposerWithDraft).toHaveBeenCalledOnce();
    expect(String(shell.openIdeComposerWithDraft.mock.calls[0]?.[0])).toContain('run-123');
  });

  it('opens the team roster for the active teammate', () => {
    const shell = mockShell();
    const showAgentDock = vi.fn();
    const showTerminalPanel = vi.fn();

    handleIdeQuickGuideAction('open-team-roster', {
      shell: shell as never,
      showAgentDock,
      showTerminalPanel,
    });

    expect(shell.revealTeamRosterForActiveEmployee).toHaveBeenCalledOnce();
    expect(showAgentDock).not.toHaveBeenCalled();
  });
});
