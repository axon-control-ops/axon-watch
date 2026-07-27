import { vi } from 'vitest';

export function mockShell(overrides: Record<string, unknown> = {}) {
  return {
    agentDockCollapsed: true,
    pendingApprovalsCount: 0,
    agentStreamActive: false,
    primaryActiveRun: null,
    activeIdeEmployeeFailureLine: null,
    activeIdeEmployeeShiftInterrupted: false,
    activeIdeEmployeeRecord: null,
    connectorsLoadState: 'loaded',
    connectorsItems: [],
    connectorsSummary: { required_unavailable: 0 },
    runtimeSummary: { watch: { connected: true } },
    currentWorkspace: { workspace_id: 'workspace_demo' },
    workspaceFilesLoadState: 'loaded',
    loadConnectors: vi.fn(),
    loadWorkspaceFiles: vi.fn(),
    focusWatchConnectors: vi.fn(),
    openIdeComposerWithDraft: vi.fn(),
    openIdeComposer: vi.fn(),
    setAgentExecutionAccess: vi.fn(),
    focusIdeSidebarView: vi.fn(),
    toggleIdeTerminalPanel: vi.fn(),
    companyEmployeesForCurrentWorkspace: [],
    editorDocuments: [],
    ideActivityView: 'explorer',
    ideExplorerCollapsed: false,
    ...overrides,
  };
}
