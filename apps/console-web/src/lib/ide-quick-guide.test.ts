import { describe, expect, it } from 'vitest';

import { buildIdeQuickGuide, ideQuickGuideActionAriaLabel, ideQuickGuideActionIsSecondary } from './ide-quick-guide';

describe('buildIdeQuickGuide', () => {
  const base = {
    layoutMode: 'ide' as const,
    agentDockCollapsed: true,
    terminalVisible: false,
    pendingApprovals: 0,
    streaming: false,
    runPhase: null,
  };

  it('returns null outside IDE layout', () => {
    expect(buildIdeQuickGuide({ ...base, layoutMode: 'operator' })).toBeNull();
  });

  it('prioritizes approval guidance', () => {
    const guide = buildIdeQuickGuide({
      ...base,
      pendingApprovals: 2,
      streaming: true,
    });

    expect(guide?.title).toContain('Approval waiting');
    expect(guide?.tone).toBe('attention');
    expect(guide?.steps.join(' ')).toContain('Ctrl/Cmd+\\');
    expect(guide?.actions).toEqual([{ id: 'expand-agent-dock', label: 'Expand agent dock' }]);
  });

  it('skips approval guidance when the agent dock is already open', () => {
    const guide = buildIdeQuickGuide({
      ...base,
      agentDockCollapsed: false,
      pendingApprovals: 1,
    });

    expect(guide == null || !guide.title.includes('Approval waiting')).toBe(true);
  });

  it('guides reopen when the agent is streaming with the dock collapsed', () => {
    const guide = buildIdeQuickGuide({
      ...base,
      streaming: true,
    });

    expect(guide?.title).toContain('responding');
    expect(guide?.tone).toBe('streaming');
    expect(guide?.steps.join(' ')).toContain('reopen strip');
    expect(guide?.actions).toEqual([{ id: 'expand-agent-dock', label: 'Expand agent dock' }]);
  });

  it('prioritizes failed teammate shift guidance when the dock is collapsed', () => {
    const failureLine = 'Last job failed: vitest assertion failed';
    const guide = buildIdeQuickGuide({
      ...base,
      employeeFailureLine: failureLine,
      employeeRetryActionLabel: 'Try again',
    });

    expect(guide?.title).toContain('Last job failed');
    expect(guide?.tone).toBe('failure');
    expect(guide?.steps[0]).toBe(failureLine);
    expect(guide?.steps.join(' ')).toContain('Try again');
    expect(guide?.actions).toEqual([
      { id: 'expand-agent-dock', label: 'Expand agent dock' },
      { id: 'retry-employee-shift', label: 'Try again' },
    ]);
  });

  it('hides roster failure sticky when Team is already open', () => {
    const guide = buildIdeQuickGuide({
      ...base,
      agentDockCollapsed: false,
      failedEmployeeCount: 1,
      failedEmployeesHint: 'Priya needs attention after a failed job.',
      teamExpanded: true,
    });
    expect(guide).toBeNull();
  });

  it('hides open-dock failure sticky when Team is already open and dock is expanded', () => {
    const guide = buildIdeQuickGuide({
      ...base,
      agentDockCollapsed: false,
      employeeFailureLine: 'Last job could not run — Cursor CLI auth timed out.',
      employeeRetryActionLabel: 'Try again',
      teamExpanded: true,
    });
    expect(guide).toBeNull();
  });

  it('uses Continue in interrupted quick-guide steps', () => {
    const guide = buildIdeQuickGuide({
      ...base,
      employeeFailureLine:
        'Last job was interrupted before it could finish — tap Continue to pick up where they left off.',
      employeeShiftInterrupted: true,
      employeeRetryActionLabel: 'Continue',
    });

    expect(guide?.steps.join(' ')).toContain('Continue');
    expect(guide?.steps.join(' ')).not.toContain('Try again in the failure banner');
    expect(guide?.actions).toContainEqual({
      id: 'retry-employee-shift',
      label: 'Continue',
    });
  });

  it('guides interrupted teammate shifts to continue rather than retry', () => {
    const guide = buildIdeQuickGuide({
      ...base,
      employeeFailureLine:
        'Last job was interrupted before it could finish — tap Continue to pick up where they left off.',
      employeeShiftInterrupted: true,
    });

    expect(guide?.title).toContain('Job interrupted');
    expect(guide?.tone).toBe('interrupted');
    expect(guide?.steps.join(' ')).toContain('Continue');
  });

  it('guides retry from the dock banner when a teammate failed with the dock already open', () => {
    const failureLine = 'Last job failed: vitest assertion failed';
    const guide = buildIdeQuickGuide({
      ...base,
      agentDockCollapsed: false,
      terminalVisible: true,
      employeeFailureLine: failureLine,
      employeeRetryActionLabel: 'Try again',
    });

    expect(guide?.title).toContain('Last job failed');
    expect(guide?.tone).toBe('failure');
    // Dock banner already shows the failure line — sticky points at Try again there.
    expect(guide?.steps[0]).toContain('Try again in the failure banner');
    expect(guide?.steps.join(' ')).toContain('agent dock composer');
    expect(guide?.actions).toEqual([{ id: 'retry-employee-shift', label: 'Try again' }]);
  });

  it('offers terminal reopen when the dock is open and a shift was interrupted', () => {
    const guide = buildIdeQuickGuide({
      ...base,
      agentDockCollapsed: false,
      terminalVisible: false,
      employeeFailureLine:
        'Last job was interrupted before it could finish — tap Continue to pick up where they left off.',
      employeeShiftInterrupted: true,
      employeeRetryActionLabel: 'Continue',
    });

    expect(guide?.title).toContain('Job interrupted');
    expect(guide?.tone).toBe('interrupted');
    expect(guide?.actions).toEqual([
      { id: 'retry-employee-shift', label: 'Continue' },
      { id: 'show-terminal', label: 'Show terminal' },
    ]);
  });

  it('keeps failed-shift guidance below approvals and streaming', () => {
    expect(
      buildIdeQuickGuide({
        ...base,
        pendingApprovals: 1,
        employeeFailureLine: 'Last job failed: timeout',
      })?.title,
    ).toContain('Approval waiting');
    expect(
      buildIdeQuickGuide({
        ...base,
        streaming: true,
        employeeFailureLine: 'Last job failed: timeout',
      })?.title,
    ).toContain('responding');
  });

  it('lists layout shortcuts when agent dock and terminal are both hidden', () => {
    const guide = buildIdeQuickGuide(base);

    expect(guide?.title).toContain('Panels closed');
    expect(guide?.tone).toBe('neutral');
    expect(guide?.steps.join(' ')).toContain('Ctrl/Cmd+J');
    expect(guide?.steps.join(' ')).toContain('Ctrl/Cmd+B');
    expect(guide?.steps.join(' ')).toContain('Ctrl/Cmd+Shift+F');
    expect(guide?.steps.join(' ')).toContain('Ctrl/Cmd+Shift+G');
    expect(guide?.actions.map((action) => action.id)).toEqual([
      'expand-agent-dock',
      'show-terminal',
    ]);
  });

  it('skips idle terminal-reopen banner when the agent dock is already open', () => {
    expect(
      buildIdeQuickGuide({
        ...base,
        agentDockCollapsed: false,
        terminalVisible: false,
      }),
    ).toBeNull();
  });

  it('guides agent dock reopen when a run is active with the dock collapsed', () => {
    const executing = buildIdeQuickGuide({
      ...base,
      runPhase: 'executing',
      terminalVisible: true,
    });
    expect(executing?.title).toContain('Run in progress');
    expect(executing?.actions).toEqual([{ id: 'expand-agent-dock', label: 'Expand agent dock' }]);

    const reviewReady = buildIdeQuickGuide({
      ...base,
      runPhase: 'review_ready',
      terminalVisible: true,
    });
    expect(reviewReady?.title).toContain('Review ready');
    expect(reviewReady?.steps.join(' ')).toContain('complete the run');
  });

  it('adds terminal reopen when a run is active with both panels collapsed', () => {
    const guide = buildIdeQuickGuide({
      ...base,
      runPhase: 'executing',
      terminalVisible: false,
    });

    expect(guide?.actions.map((action) => action.id)).toEqual([
      'expand-agent-dock',
      'show-terminal',
    ]);
    expect(guide?.steps.join(' ')).toContain('Ctrl/Cmd+J');
  });

  it('prioritizes run-aware terminal guidance when the agent dock is open', () => {
    const executing = buildIdeQuickGuide({
      ...base,
      agentDockCollapsed: false,
      terminalVisible: false,
      runPhase: 'executing',
    });
    expect(executing?.title).toContain('Terminal hidden');
    expect(executing?.tone).toBe('attention');
    expect(executing?.actions).toEqual([{ id: 'show-terminal', label: 'Show terminal' }]);

    const reviewReady = buildIdeQuickGuide({
      ...base,
      agentDockCollapsed: false,
      terminalVisible: false,
      runPhase: 'review_ready',
    });
    expect(reviewReady?.title).toContain('Terminal hidden');
    expect(reviewReady?.tone).toBe('attention');
  });

  it('guides agent dock reopen when the terminal is open but the dock is collapsed', () => {
    const guide = buildIdeQuickGuide({
      ...base,
      agentDockCollapsed: true,
      terminalVisible: true,
    });

    expect(guide?.title).toContain('Agent dock collapsed');
    expect(guide?.tone).toBe('neutral');
    expect(guide?.steps.join(' ')).toContain('Ctrl/Cmd+\\');
    expect(guide?.steps.join(' ')).toContain('activity bar');
    expect(guide?.actions).toEqual([{ id: 'expand-agent-dock', label: 'Expand agent dock' }]);
  });

  it('returns null when agent dock and terminal are both open', () => {
    expect(
      buildIdeQuickGuide({
        ...base,
        agentDockCollapsed: false,
        terminalVisible: true,
      }),
    ).toBeNull();
  });

  it('surfaces roster failure guidance when another teammate failed', () => {
    const guide = buildIdeQuickGuide({
      ...base,
      failedEmployeeCount: 1,
      failedEmployeesHint: 'Alex — Last job failed: timeout',
      rosterAlertTone: 'failure',
    });

    expect(guide?.tone).toBe('failure');
    expect(guide?.title).toContain("Teammate's last job failed");
    expect(guide?.steps[0]).toBe('Alex — Last job failed: timeout');
    expect(guide?.steps.join(' ')).toContain('Try again');
    expect(guide?.actions.map((action) => action.id)).toEqual(['open-team', 'show-terminal']);
  });

  it('uses interrupted styling when another teammate has an interrupted job', () => {
    const guide = buildIdeQuickGuide({
      ...base,
      failedEmployeeCount: 1,
      failedEmployeesHint:
        'Alex — Last job was interrupted before it could finish — tap Continue to pick up where they left off.',
      rosterAlertTone: 'interrupted',
    });

    expect(guide?.tone).toBe('interrupted');
    expect(guide?.title).toContain("Teammate's job was interrupted");
    expect(guide?.steps.join(' ')).toContain('Continue');
  });

  it('uses mixed roster copy when teammates have both failed and interrupted jobs', () => {
    const guide = buildIdeQuickGuide({
      ...base,
      failedEmployeeCount: 2,
      rosterAlertTone: 'mixed',
    });

    expect(guide?.tone).toBe('failure');
    expect(guide?.title).toContain('2 teammates need attention');
    expect(guide?.steps.join(' ')).toContain('Continue or Try again');
  });

  it('shows roster failure guidance even when agent dock and terminal are both open', () => {
    const guide = buildIdeQuickGuide({
      ...base,
      agentDockCollapsed: false,
      terminalVisible: true,
      failedEmployeeCount: 2,
      failedEmployeesHint:
        '2 teammates need attention after a failed job — select one and tap Try again, or click to talk it through.',
    });

    expect(guide?.tone).toBe('failure');
    expect(guide?.title).toContain('2 teammates need attention');
    expect(guide?.actions).toEqual([{ id: 'open-team', label: 'Open Team' }]);
  });

  it('keeps active teammate failure guidance above roster failures', () => {
    expect(
      buildIdeQuickGuide({
        ...base,
        employeeFailureLine: 'Last job failed: timeout',
        failedEmployeeCount: 2,
      })?.title,
    ).toContain('Last job failed');
  });

  it('surfaces unsaved-file guidance when Source Control is collapsed', () => {
    const guide = buildIdeQuickGuide({
      ...base,
      dirtyFileCount: 2,
      sourceControlExpanded: false,
    });

    expect(guide?.tone).toBe('attention');
    expect(guide?.title).toContain('2 unsaved files');
    expect(guide?.steps.join(' ')).toContain('Source Control');
    expect(guide?.steps.join(' ')).toContain('Ctrl/Cmd+Shift+G');
    expect(guide?.steps.join(' ')).toContain('status bar Unsaved chip and pill');
    expect(guide?.actions).toEqual([
      { id: 'open-source-control', label: 'Open Source Control' },
    ]);
  });

  it('skips unsaved-file guidance when Source Control is already open', () => {
    const guide = buildIdeQuickGuide({
      ...base,
      dirtyFileCount: 1,
      sourceControlExpanded: true,
    });

    expect(guide?.title).not.toContain('Unsaved');
  });

  it('surfaces search load-failure guidance when the file index errors', () => {
    const guide = buildIdeQuickGuide({
      ...base,
      workspaceFilesLoadState: 'error',
      searchExpanded: false,
    });

    expect(guide?.tone).toBe('attention');
    expect(guide?.title).toContain('Workspace files failed to load');
    expect(guide?.steps.join(' ')).toContain('Ctrl/Cmd+Shift+F');
    expect(guide?.steps.join(' ')).toContain('SEARCH ERR');
    expect(guide?.actions).toEqual([{ id: 'open-search', label: 'Open Search' }]);
  });

  it('skips search load-failure guidance when Search is already open', () => {
    const guide = buildIdeQuickGuide({
      ...base,
      workspaceFilesLoadState: 'error',
      searchExpanded: true,
    });

    expect(guide?.title).not.toContain('Workspace files failed to load');
  });

  it('keeps unsaved-file guidance above search load-failure nudges', () => {
    expect(
      buildIdeQuickGuide({
        ...base,
        dirtyFileCount: 2,
        workspaceFilesLoadState: 'error',
      })?.title,
    ).toContain('2 unsaved files');
  });

  it('keeps roster failure guidance above unsaved-file nudges', () => {
    expect(
      buildIdeQuickGuide({
        ...base,
        dirtyFileCount: 3,
        failedEmployeeCount: 1,
      })?.title,
    ).toContain("Teammate's last job failed");
  });
});

describe('ideQuickGuideActionIsSecondary', () => {
  it('emphasizes retry when expand is also offered', () => {
    const actions = [
      { id: 'expand-agent-dock' as const, label: 'Expand agent dock' },
      { id: 'retry-employee-shift' as const, label: 'Try again' },
    ];

    expect(ideQuickGuideActionIsSecondary('retry-employee-shift', actions)).toBe(true);
    expect(ideQuickGuideActionIsSecondary('expand-agent-dock', actions)).toBe(false);
  });

  it('keeps a lone retry action fully emphasized', () => {
    const actions = [{ id: 'retry-employee-shift' as const, label: 'Try again' }];

    expect(ideQuickGuideActionIsSecondary('retry-employee-shift', actions)).toBe(false);
  });
});

describe('ideQuickGuideActionAriaLabel', () => {
  it('expands quick-guide button labels for screen readers', () => {
    expect(
      ideQuickGuideActionAriaLabel({ id: 'open-connectors', label: 'Open connectors' }),
    ).toContain('Mission Control');
    expect(
      ideQuickGuideActionAriaLabel({ id: 'expand-agent-dock', label: 'Expand agent dock' }),
    ).toContain('right edge');
    expect(
      ideQuickGuideActionAriaLabel({ id: 'show-terminal', label: 'Show terminal' }),
    ).toContain('below the editor');
    expect(
      ideQuickGuideActionAriaLabel({ id: 'retry-employee-shift', label: 'Continue' }),
    ).toContain('agent dock composer');
    expect(
      ideQuickGuideActionAriaLabel({ id: 'open-team', label: 'Open Team' }),
    ).toContain('left activity bar');
    expect(
      ideQuickGuideActionAriaLabel({
        id: 'open-source-control',
        label: 'Open Source Control',
      }),
    ).toContain('Source Control sidebar');
  });
});
