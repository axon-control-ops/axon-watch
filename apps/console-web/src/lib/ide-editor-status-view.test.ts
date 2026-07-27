import { describe, expect, it } from 'vitest';

import type { CompanyEmployeeRecord } from '../contracts/canonical';
import {
  buildIdeEditorStatusAgentChip,
  buildIdeEditorStatusConnectorChip,
  buildIdeEditorStatusGitChip,
  buildIdeEditorStatusSearchChip,
  buildIdeEditorStatusTeamChip,
  buildIdeEditorStatusTerminalChip,
} from './ide-editor-status-view';

function employee(overrides: Partial<CompanyEmployeeRecord> = {}): CompanyEmployeeRecord {
  return {
    employee_id: 'e1',
    workspace_id: 'workspace_demo',
    name: 'Shell Craft',
    role: 'frontend',
    role_label: 'UI/UX',
    schedule: 'continuous',
    schedule_label: 'Continuous',
    status: 'idle',
    owns: 'console UI/UX, dock, and shell polish',
    enabled: true,
    primary: false,
    ...overrides,
  };
}

describe('buildIdeEditorStatusConnectorChip', () => {
  const base = {
    connectorsLoadState: 'loaded' as const,
    watchConnected: true,
    items: [] as const,
  };

  it('shows a compact required-down chip in the editor status bar', () => {
    expect(
      buildIdeEditorStatusConnectorChip({
        ...base,
        summary: { required_unavailable: 2 },
      }),
    ).toEqual({
      id: 'connector-required-alert',
      label: '2 REQ DOWN',
      tone: 'warning',
      title: 'Required connector down — switch to Mission Control connectors',
      ariaLabel: '2 REQ DOWN. Required connector down — switch to Mission Control connectors.',
    });
  });

  it('uses singular copy for one required connector', () => {
    expect(
      buildIdeEditorStatusConnectorChip({
        ...base,
        summary: { required_unavailable: 1 },
      })?.label,
    ).toBe('1 REQ DOWN');
  });

  it('shows a compact legacy-offline chip when optional Axon Local is down', () => {
    expect(
      buildIdeEditorStatusConnectorChip({
        ...base,
        summary: { required_unavailable: 0 },
        items: [
          {
            connector_id: 'axon_local',
            display_name: 'Axon Local',
            status: 'unavailable',
            required: false,
          },
        ],
      }),
    ).toMatchObject({
      id: 'connector-glance',
      label: 'LEGACY OFFLINE',
      tone: 'default',
    });
  });

  it('labels degraded legacy status distinctly', () => {
    expect(
      buildIdeEditorStatusConnectorChip({
        ...base,
        summary: { required_unavailable: 0 },
        items: [
          {
            connector_id: 'axon_local',
            display_name: 'Axon Local',
            status: 'degraded',
            required: false,
          },
        ],
      })?.label,
    ).toBe('LEGACY DEGRADED');
  });

  it('hides the chip when connectors are healthy', () => {
    expect(
      buildIdeEditorStatusConnectorChip({
        ...base,
        summary: { required_unavailable: 0 },
        items: [
          {
            connector_id: 'axon_local',
            display_name: 'Axon Local',
            status: 'ok',
            required: false,
          },
        ],
      }),
    ).toBeNull();
  });

  it('shows watch offline instead of stale connector counts', () => {
    expect(
      buildIdeEditorStatusConnectorChip({
        ...base,
        watchConnected: false,
        summary: { required_unavailable: 2 },
      }),
    ).toMatchObject({
      id: 'watch-offline',
      label: 'WATCH OFFLINE',
      tone: 'warning',
    });
    expect(
      buildIdeEditorStatusConnectorChip({
        ...base,
        watchConnected: false,
        summary: { required_unavailable: 0 },
        items: [
          {
            connector_id: 'axon_local',
            display_name: 'Axon Local',
            status: 'unavailable',
            required: false,
          },
        ],
      })?.id,
    ).toBe('watch-offline');
  });
});

describe('buildIdeEditorStatusGitChip', () => {
  it('returns null when Source Control is already open', () => {
    expect(
      buildIdeEditorStatusGitChip({ dirtyFileCount: 2, sourceControlExpanded: true }),
    ).toBeNull();
  });

  it('returns null when every file tab is saved', () => {
    expect(
      buildIdeEditorStatusGitChip({ dirtyFileCount: 0, sourceControlExpanded: false }),
    ).toBeNull();
  });

  it('surfaces a compact unsaved count when file tabs need saving', () => {
    expect(
      buildIdeEditorStatusGitChip({ dirtyFileCount: 1, sourceControlExpanded: false }),
    ).toMatchObject({
      label: '1 UNSAVED',
      count: 1,
    });
    expect(
      buildIdeEditorStatusGitChip({ dirtyFileCount: 3, sourceControlExpanded: false }),
    ).toMatchObject({
      label: '3 UNSAVED',
      count: 3,
    });
    expect(
      buildIdeEditorStatusGitChip({ dirtyFileCount: 2, sourceControlExpanded: false })?.ariaLabel,
    ).toContain('2 unsaved files');
    expect(
      buildIdeEditorStatusGitChip({ dirtyFileCount: 2, sourceControlExpanded: false })?.ariaLabel,
    ).toContain('Source Control sidebar');
  });
});

describe('buildIdeEditorStatusSearchChip', () => {
  it('returns null when Search is already expanded or files loaded cleanly', () => {
    expect(
      buildIdeEditorStatusSearchChip({
        loadState: 'error',
        hasWorkspace: true,
        searchExpanded: true,
      }),
    ).toBeNull();
    expect(
      buildIdeEditorStatusSearchChip({
        loadState: 'loaded',
        hasWorkspace: true,
        searchExpanded: false,
      }),
    ).toBeNull();
  });

  it('surfaces a compact chip when the workspace file index fails to load', () => {
    expect(
      buildIdeEditorStatusSearchChip({
        loadState: 'error',
        hasWorkspace: true,
        searchExpanded: false,
      }),
    ).toMatchObject({
      label: 'SEARCH ERR',
    });
    expect(
      buildIdeEditorStatusSearchChip({
        loadState: 'error',
        hasWorkspace: true,
        searchExpanded: false,
      })?.ariaLabel,
    ).toContain('Workspace files failed to load');
    expect(
      buildIdeEditorStatusSearchChip({
        loadState: 'error',
        hasWorkspace: true,
        searchExpanded: false,
      })?.ariaLabel,
    ).toContain('Search sidebar');
  });
});

describe('buildIdeEditorStatusTeamChip', () => {
  it('returns null when Team is already expanded or everyone is healthy', () => {
    expect(
      buildIdeEditorStatusTeamChip({
        employees: [employee({ last_outcome: 'failed', last_outcome_detail: 'timeout' })],
        teamExpanded: true,
      }),
    ).toBeNull();
    expect(
      buildIdeEditorStatusTeamChip({
        employees: [employee()],
        teamExpanded: false,
      }),
    ).toBeNull();
  });

  it('surfaces failed and interrupted counts when the Team sidebar is collapsed', () => {
    expect(
      buildIdeEditorStatusTeamChip({
        employees: [employee({ last_outcome: 'failed', last_outcome_detail: 'timeout' })],
        teamExpanded: false,
      }),
    ).toMatchObject({
      label: '1 FAILED',
      tone: 'failure',
      count: 1,
    });

    expect(
      buildIdeEditorStatusTeamChip({
        employees: [
          employee({
            employee_id: 'e2',
            name: 'Alex',
            last_outcome: 'failed',
            last_outcome_detail: 'run interrupted by control-plane restart',
          }),
        ],
        teamExpanded: false,
      }),
    ).toMatchObject({
      label: '1 INTERRUPTED',
      tone: 'interrupted',
      count: 1,
    });

    const mixed = buildIdeEditorStatusTeamChip({
      employees: [
        employee({ last_outcome: 'failed', last_outcome_detail: 'timeout' }),
        employee({
          employee_id: 'e2',
          name: 'Alex',
          last_outcome: 'failed',
          last_outcome_detail: 'run interrupted by control-plane restart',
        }),
      ],
      teamExpanded: false,
    });

    expect(mixed).toMatchObject({
      label: '2 NEED ATTENTION',
      tone: 'mixed',
      count: 2,
    });
    expect(mixed?.ariaLabel).toContain('Team sidebar');
  });
});

describe('buildIdeEditorStatusTerminalChip', () => {
  it('returns null when the terminal panel is already visible', () => {
    expect(
      buildIdeEditorStatusTerminalChip({ terminalVisible: true, runPhase: 'executing' }),
    ).toBeNull();
  });

  it('surfaces run phase hints when the terminal is hidden', () => {
    const chip = buildIdeEditorStatusTerminalChip({
      terminalVisible: false,
      runPhase: 'executing',
    });

    expect(chip).toMatchObject({
      label: 'TERMINAL',
      showPulse: true,
      executing: true,
      reviewReady: false,
    });
    expect(chip?.title).toContain('Run in progress');
  });
});

describe('buildIdeEditorStatusAgentChip', () => {
  it('returns null when the agent dock is already expanded', () => {
    expect(
      buildIdeEditorStatusAgentChip({
        agentDockCollapsed: false,
        state: { streaming: true, pendingApprovals: 1, runPhase: 'executing' },
      }),
    ).toBeNull();
  });

  it('surfaces approval badge and attention styling when approvals are waiting', () => {
    const chip = buildIdeEditorStatusAgentChip({
      agentDockCollapsed: true,
      state: { streaming: false, pendingApprovals: 2, runPhase: null },
    });

    expect(chip).toMatchObject({
      label: 'AGENT',
      showBadge: 2,
      showPulse: false,
      approvals: true,
      alive: true,
    });
  });

  it('surfaces a pulse when a run needs the dock but no approvals are waiting', () => {
    const chip = buildIdeEditorStatusAgentChip({
      agentDockCollapsed: true,
      state: { streaming: false, pendingApprovals: 0, runPhase: 'review_ready' },
    });

    expect(chip).toMatchObject({
      showBadge: null,
      showPulse: true,
      reviewReady: true,
      alive: true,
      failure: false,
      interrupted: false,
    });
  });

  it('surfaces failure styling when a teammate hard-failed with the dock collapsed', () => {
    const chip = buildIdeEditorStatusAgentChip({
      agentDockCollapsed: true,
      state: {
        streaming: false,
        pendingApprovals: 0,
        runPhase: null,
        employeeFailureLine: 'Last job failed: timeout',
      },
    });

    expect(chip).toMatchObject({
      showPulse: true,
      failure: true,
      interrupted: false,
    });
    expect(chip?.title).toContain('Last job failed');
  });

  it('surfaces interrupted styling when a teammate shift was cut short', () => {
    const chip = buildIdeEditorStatusAgentChip({
      agentDockCollapsed: true,
      state: {
        streaming: false,
        pendingApprovals: 0,
        runPhase: null,
        employeeFailureLine:
          'Last job was interrupted before it could finish — tap Continue to pick up where they left off.',
        employeeShiftInterrupted: true,
      },
    });

    expect(chip).toMatchObject({
      showPulse: true,
      failure: false,
      interrupted: true,
    });
    expect(chip?.title).toContain('Job interrupted');
  });

  it('surfaces SPEAKING when narration is active with the dock collapsed', () => {
    const chip = buildIdeEditorStatusAgentChip({
      agentDockCollapsed: true,
      state: {
        streaming: false,
        pendingApprovals: 0,
        runPhase: null,
        speaking: true,
      },
    });

    expect(chip).toMatchObject({
      label: 'SPEAKING',
      speaking: true,
      showPulse: true,
      alive: true,
    });
    expect(chip?.title).toContain('Speaking');
  });
});
