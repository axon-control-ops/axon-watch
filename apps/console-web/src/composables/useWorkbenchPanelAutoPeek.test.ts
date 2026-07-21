import { describe, expect, it, vi } from 'vitest';
import { computed, ref } from 'vue';

import { useWorkbenchPanelAutoPeek } from './useWorkbenchPanelAutoPeek';

function mockShell(overrides: Record<string, unknown> = {}) {
  return {
    agentDockCollapsed: true,
    pendingApprovalsCount: 0,
    agentStreamActive: false,
    agentStreamMessageId: null,
    primaryActiveRun: null,
    activeIdeEmployeeFailureLine: null,
    activeIdeEmployeeRecord: null,
    ...overrides,
  };
}

describe('useWorkbenchPanelAutoPeek', () => {
  it('does not auto-open the terminal; still opens the agent dock once when a run starts executing', () => {
    const onShowTerminal = vi.fn();
    const onShowAgentDock = vi.fn();
    const shell = mockShell({
      primaryActiveRun: { run_id: 'run_abc', phase: 'executing' },
    });

    useWorkbenchPanelAutoPeek({
      shell: shell as never,
      workbenchLayoutMode: computed(() => 'ide'),
      terminalPanelVisible: ref(false),
      onShowTerminal,
      onShowAgentDock,
    });

    expect(onShowTerminal).not.toHaveBeenCalled();
    expect(onShowAgentDock).toHaveBeenCalledOnce();
  });

  it('opens the agent dock once when approvals arrive', () => {
    const onShowTerminal = vi.fn();
    const onShowAgentDock = vi.fn();
    const shell = mockShell({ pendingApprovalsCount: 1 });

    useWorkbenchPanelAutoPeek({
      shell: shell as never,
      workbenchLayoutMode: computed(() => 'ide'),
      terminalPanelVisible: ref(false),
      onShowTerminal,
      onShowAgentDock,
    });

    expect(onShowAgentDock).toHaveBeenCalledOnce();
    expect(onShowTerminal).not.toHaveBeenCalled();
  });

  it('opens the agent dock once when a teammate shift fails', () => {
    const onShowTerminal = vi.fn();
    const onShowAgentDock = vi.fn();
    const shell = mockShell({
      activeIdeEmployeeFailureLine: 'Last shift failed: vitest assertion failed',
      activeIdeEmployeeRecord: {
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
        last_run_id: 'run_abc',
        last_outcome_detail: 'vitest assertion failed',
      },
    });

    useWorkbenchPanelAutoPeek({
      shell: shell as never,
      workbenchLayoutMode: computed(() => 'ide'),
      terminalPanelVisible: ref(false),
      onShowTerminal,
      onShowAgentDock,
    });

    expect(onShowAgentDock).toHaveBeenCalledOnce();
    expect(onShowTerminal).not.toHaveBeenCalled();
  });
});
