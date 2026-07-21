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

    expect(guide?.title).not.toContain('Approval waiting');
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
    const failureLine = 'Last shift failed: vitest assertion failed';
    const guide = buildIdeQuickGuide({
      ...base,
      employeeFailureLine: failureLine,
      employeeRetryActionLabel: 'Retry shift',
    });

    expect(guide?.title).toContain('Last shift failed');
    expect(guide?.tone).toBe('failure');
    expect(guide?.steps[0]).toBe(failureLine);
    expect(guide?.steps.join(' ')).toContain('Retry shift');
    expect(guide?.actions).toEqual([
      { id: 'expand-agent-dock', label: 'Expand agent dock' },
      { id: 'retry-employee-shift', label: 'Retry shift' },
    ]);
  });

  it('uses Continue shift in interrupted quick-guide steps', () => {
    const guide = buildIdeQuickGuide({
      ...base,
      employeeFailureLine:
        'Last shift interrupted before it could finish — use Continue shift to pick up where you left off.',
      employeeShiftInterrupted: true,
      employeeRetryActionLabel: 'Continue shift',
    });

    expect(guide?.steps.join(' ')).toContain('Continue shift');
    expect(guide?.steps.join(' ')).not.toContain('Retry shift in the failure banner');
    expect(guide?.actions).toContainEqual({
      id: 'retry-employee-shift',
      label: 'Continue shift',
    });
  });

  it('guides interrupted teammate shifts to continue rather than retry', () => {
    const guide = buildIdeQuickGuide({
      ...base,
      employeeFailureLine:
        'Last shift interrupted before it could finish — use Continue shift to pick up where you left off.',
      employeeShiftInterrupted: true,
    });

    expect(guide?.title).toContain('Shift interrupted');
    expect(guide?.tone).toBe('interrupted');
    expect(guide?.steps.join(' ')).toContain('Continue shift');
  });

  it('guides retry from the dock banner when a teammate failed with the dock already open', () => {
    const failureLine = 'Last shift failed: vitest assertion failed';
    const guide = buildIdeQuickGuide({
      ...base,
      agentDockCollapsed: false,
      terminalVisible: true,
      employeeFailureLine: failureLine,
      employeeRetryActionLabel: 'Retry shift',
    });

    expect(guide?.title).toContain('Last shift failed');
    expect(guide?.tone).toBe('failure');
    expect(guide?.steps[0]).toBe(failureLine);
    expect(guide?.steps.join(' ')).toContain('Retry shift');
    expect(guide?.steps.join(' ')).toContain('agent dock composer');
    expect(guide?.actions).toEqual([{ id: 'retry-employee-shift', label: 'Retry shift' }]);
  });

  it('offers terminal reopen when the dock is open and a shift was interrupted', () => {
    const guide = buildIdeQuickGuide({
      ...base,
      agentDockCollapsed: false,
      terminalVisible: false,
      employeeFailureLine:
        'Last shift interrupted before it could finish — use Continue shift to pick up where you left off.',
      employeeShiftInterrupted: true,
      employeeRetryActionLabel: 'Continue shift',
    });

    expect(guide?.title).toContain('Shift interrupted');
    expect(guide?.tone).toBe('interrupted');
    expect(guide?.actions).toEqual([
      { id: 'retry-employee-shift', label: 'Continue shift' },
      { id: 'show-terminal', label: 'Show terminal' },
    ]);
  });

  it('keeps failed-shift guidance below approvals and streaming', () => {
    expect(
      buildIdeQuickGuide({
        ...base,
        pendingApprovals: 1,
        employeeFailureLine: 'Last shift failed: timeout',
      })?.title,
    ).toContain('Approval waiting');
    expect(
      buildIdeQuickGuide({
        ...base,
        streaming: true,
        employeeFailureLine: 'Last shift failed: timeout',
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

  it('guides terminal reopen when the agent dock is open but the terminal is hidden', () => {
    const guide = buildIdeQuickGuide({
      ...base,
      agentDockCollapsed: false,
      terminalVisible: false,
    });

    expect(guide?.title).toContain('Terminal hidden');
    expect(guide?.tone).toBe('neutral');
    expect(guide?.steps.join(' ')).toContain('Ctrl/Cmd+J');
    expect(guide?.steps.join(' ')).toContain('bottom reopen strip');
    expect(guide?.steps.join(' ')).toContain('activity bar');
    expect(guide?.actions).toEqual([{ id: 'show-terminal', label: 'Show terminal' }]);
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
    expect(executing?.title).toContain('Run in progress');
    expect(executing?.tone).toBe('attention');
    expect(executing?.actions).toEqual([{ id: 'show-terminal', label: 'Show terminal' }]);

    const reviewReady = buildIdeQuickGuide({
      ...base,
      agentDockCollapsed: false,
      terminalVisible: false,
      runPhase: 'review_ready',
    });
    expect(reviewReady?.title).toContain('Review ready');
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
      failedEmployeesHint: 'Alex — Last shift failed: timeout',
      rosterAlertTone: 'failure',
    });

    expect(guide?.tone).toBe('failure');
    expect(guide?.title).toContain('Teammate shift failed');
    expect(guide?.steps[0]).toBe('Alex — Last shift failed: timeout');
    expect(guide?.steps.join(' ')).toContain('Retry shift');
    expect(guide?.actions.map((action) => action.id)).toEqual(['open-team', 'show-terminal']);
  });

  it('uses interrupted styling when another teammate has an interrupted shift', () => {
    const guide = buildIdeQuickGuide({
      ...base,
      failedEmployeeCount: 1,
      failedEmployeesHint:
        'Alex — Last shift interrupted before it could finish — use Continue shift to pick up where you left off.',
      rosterAlertTone: 'interrupted',
    });

    expect(guide?.tone).toBe('interrupted');
    expect(guide?.title).toContain('Teammate shift interrupted');
    expect(guide?.steps.join(' ')).toContain('Continue shift');
  });

  it('uses mixed roster copy when teammates have both failed and interrupted shifts', () => {
    const guide = buildIdeQuickGuide({
      ...base,
      failedEmployeeCount: 2,
      rosterAlertTone: 'mixed',
    });

    expect(guide?.tone).toBe('failure');
    expect(guide?.title).toContain('2 teammates need attention');
    expect(guide?.steps.join(' ')).toContain('Continue shift or Retry shift');
  });

  it('shows roster failure guidance even when agent dock and terminal are both open', () => {
    const guide = buildIdeQuickGuide({
      ...base,
      agentDockCollapsed: false,
      terminalVisible: true,
      failedEmployeeCount: 2,
      failedEmployeesHint:
        '2 teammates need attention after a failed shift — select one for Retry shift, or click to talk it through.',
    });

    expect(guide?.tone).toBe('failure');
    expect(guide?.title).toContain('2 teammates need attention');
    expect(guide?.actions).toEqual([{ id: 'open-team', label: 'Open Team' }]);
  });

  it('keeps active teammate failure guidance above roster failures', () => {
    expect(
      buildIdeQuickGuide({
        ...base,
        employeeFailureLine: 'Last shift failed: timeout',
        failedEmployeeCount: 2,
      })?.title,
    ).toContain('Last shift failed');
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
    ).toContain('Teammate shift failed');
  });
});

describe('ideQuickGuideActionIsSecondary', () => {
  it('emphasizes retry when expand is also offered', () => {
    const actions = [
      { id: 'expand-agent-dock' as const, label: 'Expand agent dock' },
      { id: 'retry-employee-shift' as const, label: 'Retry shift' },
    ];

    expect(ideQuickGuideActionIsSecondary('retry-employee-shift', actions)).toBe(true);
    expect(ideQuickGuideActionIsSecondary('expand-agent-dock', actions)).toBe(false);
  });

  it('keeps a lone retry action fully emphasized', () => {
    const actions = [{ id: 'retry-employee-shift' as const, label: 'Retry shift' }];

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
      ideQuickGuideActionAriaLabel({ id: 'retry-employee-shift', label: 'Continue shift' }),
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
