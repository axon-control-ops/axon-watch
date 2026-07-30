import { describe, expect, it, vi } from 'vitest';
import { computed, ref } from 'vue';

vi.mock('../lib/agent-dock-composer-focus', () => ({
  focusAgentDockComposerInput: vi.fn(),
}));

import {
  ensureWorkspaceFilesLoaded,
  useIdeEditorStatusBar,
} from './useIdeEditorStatusBar';
import { mockShell } from './useIdeEditorStatusBar.fixture';

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

  it('shows watch-offline chip and suppresses stale connector-down guidance when watch is disconnected', () => {
    const shell = mockShell({
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
      tone: 'warning',
    });
    expect(ideQuickGuide.value?.title).toContain('Watch offline');
    expect(ideQuickGuide.value?.title).not.toContain('connectors down');
    expect(ideQuickGuide.value?.actions.map((action) => action.id)).toContain(
      'open-connectors',
    );
  });

  it('surfaces interrupted teammate guidance through the quick guide', () => {
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
      last_outcome_detail: 'Agent exited with status 143 (SIGTERM)',
    };
    const shell = mockShell({
      activeIdeEmployeeFailureLine:
        'Last job was interrupted before it could finish — tap Continue to pick up where they left off.',
      activeIdeEmployeeShiftInterrupted: true,
      activeIdeEmployeeRecord: employee,
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
    expect(ideQuickGuide.value?.title).toContain('Job interrupted');
    expect(ideQuickGuide.value?.actions).toContainEqual({
      id: 'retry-employee-shift',
      label: 'Continue',
    });
  });

  it('surfaces roster failure guidance when another teammate failed', () => {
    const shell = mockShell({
      companyEmployeesForCurrentWorkspace: [
        {
          employee_id: 'e2',
          workspace_id: 'workspace_demo',
          name: 'Alex',
          role: 'backend',
          role_label: 'Backend',
          schedule: 'continuous',
          schedule_label: 'Continuous',
          status: 'idle',
          owns: 'API',
          enabled: true,
          primary: false,
          last_outcome: 'failed',
          last_outcome_detail: 'timeout',
        },
      ],
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
      })),
    });

    expect(ideQuickGuide.value?.tone).toBe('failure');
    expect(ideQuickGuide.value?.title).toContain("Teammate's last job failed");
    expect(ideQuickGuide.value?.actions.map((action) => action.id)).toContain('open-team');
  });

  it('surfaces a Team status-bar chip when roster teammates need attention', () => {
    const shell = mockShell({
      companyEmployeesForCurrentWorkspace: [
        {
          employee_id: 'e2',
          workspace_id: 'workspace_demo',
          name: 'Alex',
          role: 'backend',
          role_label: 'Backend',
          schedule: 'continuous',
          schedule_label: 'Continuous',
          status: 'idle',
          owns: 'API',
          enabled: true,
          primary: false,
          last_outcome: 'failed',
          last_outcome_detail: 'timeout',
        },
      ],
      ideActivityView: 'explorer',
    });
    const { ideEditorStatusTeamChip } = useIdeEditorStatusBar({
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

    expect(ideEditorStatusTeamChip.value).toMatchObject({
      label: '1 FAILED',
      tone: 'failure',
      count: 1,
    });

    const expanded = useIdeEditorStatusBar({
      shell: {
        ...shell,
        ideActivityView: 'team',
        ideExplorerCollapsed: false,
      } as never,
      workbenchLayoutMode: computed(() => 'ide'),
      terminalPanelVisible: ref(false),
      terminalReopenRunPhase: computed(() => null),
      agentDockReopenState: computed(() => ({
        streaming: false,
        pendingApprovals: 0,
        runPhase: null,
      })),
    });
    expect(expanded.ideEditorStatusTeamChip.value).toBeNull();
  });

  it('uses interrupted quick-guide styling when another teammate has an interrupted job', () => {
    const shell = mockShell({
      companyEmployeesForCurrentWorkspace: [
        {
          employee_id: 'e2',
          workspace_id: 'workspace_demo',
          name: 'Alex',
          role: 'backend',
          role_label: 'Backend',
          schedule: 'continuous',
          schedule_label: 'Continuous',
          status: 'idle',
          owns: 'API',
          enabled: true,
          primary: false,
          last_outcome: 'failed',
          last_outcome_detail: 'run interrupted by control-plane restart',
        },
      ],
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
      })),
    });

    expect(ideQuickGuide.value?.tone).toBe('interrupted');
    expect(ideQuickGuide.value?.title).toContain("Teammate's job was interrupted");
    expect(ideQuickGuide.value?.steps.join(' ')).toContain('Continue');
  });

  it('surfaces unsaved-file guidance from dirty editor tabs', () => {
    const shell = mockShell({
      editorDocuments: [
        { source: 'file', dirty: true },
        { source: 'file', dirty: true },
        { source: 'scratch', dirty: true },
      ],
      ideActivityView: 'explorer',
    });
    const { ideQuickGuide, ideEditorStatusGitChip } = useIdeEditorStatusBar({
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

    expect(ideQuickGuide.value?.tone).toBe('attention');
    expect(ideQuickGuide.value?.title).toContain('2 unsaved files');
    expect(ideQuickGuide.value?.actions.map((action) => action.id)).toContain(
      'open-source-control',
    );
    expect(ideEditorStatusGitChip.value).toMatchObject({
      label: '2 UNSAVED',
      count: 2,
    });
  });

  it('hides the git chip when Source Control is already expanded', () => {
    const shell = mockShell({
      editorDocuments: [{ source: 'file', dirty: true }],
      ideActivityView: 'git',
      ideExplorerCollapsed: false,
    });
    const { ideEditorStatusGitChip } = useIdeEditorStatusBar({
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

    expect(ideEditorStatusGitChip.value).toBeNull();
  });

  it('surfaces search failure guidance and chip when the file index fails to load', () => {
    const shell = mockShell({
      workspaceFilesLoadState: 'error',
      ideActivityView: 'explorer',
    });
    const { ideQuickGuide, ideEditorStatusSearchChip } = useIdeEditorStatusBar({
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

    expect(ideQuickGuide.value?.title).toContain('Workspace files failed to load');
    expect(ideQuickGuide.value?.actions.map((action) => action.id)).toContain('open-search');
    expect(ideEditorStatusSearchChip.value).toMatchObject({
      label: 'SEARCH ERR',
    });
  });

  it('hides the search chip when Search is already expanded', () => {
    const shell = mockShell({
      workspaceFilesLoadState: 'error',
      ideActivityView: 'search',
      ideExplorerCollapsed: false,
    });
    const { ideEditorStatusSearchChip } = useIdeEditorStatusBar({
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

    expect(ideEditorStatusSearchChip.value).toBeNull();
  });
});

describe('ensureWorkspaceFilesLoaded', () => {
  it('loads files when the index is still idle', () => {
    const shell = mockShell({ workspaceFilesLoadState: 'idle' });

    ensureWorkspaceFilesLoaded(shell as never);

    expect(shell.loadWorkspaceFiles).toHaveBeenCalledOnce();
  });

  it('retries after a failed file-index fetch', () => {
    const shell = mockShell({ workspaceFilesLoadState: 'error' });

    ensureWorkspaceFilesLoaded(shell as never);

    expect(shell.loadWorkspaceFiles).toHaveBeenCalledOnce();
  });

  it('does not reload while a fetch is in flight or already cached', () => {
    const loadingShell = mockShell({ workspaceFilesLoadState: 'loading' });
    const loadedShell = mockShell({ workspaceFilesLoadState: 'loaded' });

    ensureWorkspaceFilesLoaded(loadingShell as never);
    ensureWorkspaceFilesLoaded(loadedShell as never);

    expect(loadingShell.loadWorkspaceFiles).not.toHaveBeenCalled();
    expect(loadedShell.loadWorkspaceFiles).not.toHaveBeenCalled();
  });

  it('skips when no workspace is selected', () => {
    const shell = mockShell({
      currentWorkspace: null,
      workspaceFilesLoadState: 'idle',
    });

    ensureWorkspaceFilesLoaded(shell as never);

    expect(shell.loadWorkspaceFiles).not.toHaveBeenCalled();
  });
});
