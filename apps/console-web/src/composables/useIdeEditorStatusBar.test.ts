import { describe, expect, it, vi } from 'vitest';
import { computed, ref } from 'vue';

import {
  handleIdeQuickGuideAction,
  openWatchConnectors,
  useIdeEditorStatusBar,
} from './useIdeEditorStatusBar';

function mockShell(overrides: Record<string, unknown> = {}) {
  return {
    agentDockCollapsed: true,
    pendingApprovalsCount: 0,
    agentStreamActive: false,
    primaryActiveRun: null,
    activeIdeEmployeeFailureLine: null,
    activeIdeEmployeeShiftInterrupted: false,
    connectorsLoadState: 'loaded',
    connectorsItems: [],
    connectorsSummary: { required_unavailable: 0 },
    runtimeSummary: { watch: { connected: true } },
    loadConnectors: vi.fn(),
    focusWatchConnectors: vi.fn(),
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
    expect(ideQuickGuide.value?.title).toContain('Shift interrupted');
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
});
