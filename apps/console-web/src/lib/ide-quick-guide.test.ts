import { describe, expect, it } from 'vitest';

import { buildIdeQuickGuide } from './ide-quick-guide';

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

  it('prioritizes required connector guidance when idle and probes are down', () => {
    const guide = buildIdeQuickGuide({
      ...base,
      requiredConnectorsUnavailable: 2,
    });

    expect(guide?.tone).toBe('attention');
    expect(guide?.title).toContain('2 required connectors down');
    expect(guide?.steps.join(' ')).toContain('Reprobe');
    expect(guide?.actions.map((action) => action.id)).toEqual([
      'open-connectors',
      'show-terminal',
    ]);
  });

  it('surfaces legacy connector guidance when optional Axon Local is offline', () => {
    const guide = buildIdeQuickGuide({
      ...base,
      terminalVisible: true,
      legacyConnectorGlanceVisible: true,
    });

    expect(guide?.title).toContain('Legacy Axon Local');
    expect(guide?.steps.join(' ')).toContain('LEGACY OFFLINE');
    expect(guide?.actions).toEqual([{ id: 'open-connectors', label: 'Open connectors' }]);
  });

  it('does not override run guidance when a run is active', () => {
    const guide = buildIdeQuickGuide({
      ...base,
      runPhase: 'executing',
      requiredConnectorsUnavailable: 1,
    });

    expect(guide?.title).toContain('Run in progress');
    expect(guide?.actions.map((action) => action.id)).toEqual([
      'expand-agent-dock',
      'show-terminal',
    ]);
  });
});
