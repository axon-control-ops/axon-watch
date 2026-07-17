import { describe, expect, it } from 'vitest';

import { buildOperatorQuickGuide } from './operator-quick-guide';

describe('buildOperatorQuickGuide', () => {
  const base = {
    pendingApprovals: 0,
    layoutMode: 'operator' as const,
    terminalVisible: true,
  };

  it('returns review_ready guidance in operator mode', () => {
    const guide = buildOperatorQuickGuide({
      ...base,
      runPhase: 'review_ready',
      hasActiveRun: true,
    });

    expect(guide?.title).toContain('Review ready');
    expect(guide?.steps.join(' ')).toContain('COMPLETE RUN');
    expect(guide?.steps.join(' ')).toContain('Ctrl/Cmd+J');
    expect(guide?.steps.join(' ')).toContain('multi-step');
    expect(guide?.actions).toEqual([]);
  });

  it('returns executing guidance with terminal shortcut', () => {
    const guide = buildOperatorQuickGuide({
      ...base,
      runPhase: 'executing',
      hasActiveRun: true,
    });

    expect(guide?.steps.join(' ')).toContain('Ctrl/Cmd+J');
  });

  it('prioritizes terminal reopen when a run is executing with the terminal hidden', () => {
    const guide = buildOperatorQuickGuide({
      ...base,
      runPhase: 'executing',
      hasActiveRun: true,
      terminalVisible: false,
    });

    expect(guide?.title).toContain('terminal hidden');
    expect(guide?.steps[0]).toContain('Ctrl/Cmd+J');
    expect(guide?.steps.join(' ')).toContain('Terminal dock strip');
    expect(guide?.actions).toEqual([{ id: 'show-terminal', label: 'Open terminal' }]);
  });

  it('prioritizes terminal reopen when review is ready with the terminal hidden', () => {
    const guide = buildOperatorQuickGuide({
      ...base,
      runPhase: 'review_ready',
      hasActiveRun: true,
      terminalVisible: false,
    });

    expect(guide?.title).toContain('open terminal');
    expect(guide?.steps[0]).toContain('Ctrl/Cmd+J');
    expect(guide?.actions).toEqual([{ id: 'show-terminal', label: 'Open terminal' }]);
  });

  it('returns idle guidance when no run is active and terminal is open', () => {
    const guide = buildOperatorQuickGuide({
      ...base,
      runPhase: null,
      hasActiveRun: false,
      terminalVisible: true,
    });

    expect(guide?.title).toContain('Idle');
    expect(guide?.steps.join(' ')).toContain('git status');
    expect(guide?.steps.join(' ')).toContain('Hide terminal');
    expect(guide?.steps.join(' ')).toContain('agent dock');
    expect(guide?.actions).toEqual([{ id: 'switch-to-ide', label: 'Switch to IDE' }]);
  });

  it('prioritizes terminal reopen guidance when idle with terminal hidden', () => {
    const guide = buildOperatorQuickGuide({
      ...base,
      runPhase: null,
      hasActiveRun: false,
      terminalVisible: false,
    });

    expect(guide?.title).toContain('Terminal hidden');
    expect(guide?.steps.join(' ')).toContain('Terminal dock strip');
    expect(guide?.steps.join(' ')).toContain('Ctrl/Cmd+J');
    expect(guide?.actions.map((action) => action.id)).toEqual(['show-terminal', 'switch-to-ide']);
  });

  it('surfaces connector guidance when optional legacy Axon Local is offline', () => {
    const guide = buildOperatorQuickGuide({
      ...base,
      runPhase: null,
      hasActiveRun: false,
      terminalVisible: true,
      legacyConnectorGlanceVisible: true,
    });

    expect(guide?.title).toContain('legacy Axon Local');
    expect(guide?.steps.join(' ')).toContain('LEGACY AXON LOCAL OFFLINE');
    expect(guide?.actions.map((action) => action.id)).toEqual([
      'open-connectors',
      'switch-to-ide',
    ]);
  });

  it('adds connector guidance when idle with terminal hidden and legacy offline', () => {
    const guide = buildOperatorQuickGuide({
      ...base,
      runPhase: null,
      hasActiveRun: false,
      terminalVisible: false,
      legacyConnectorGlanceVisible: true,
    });

    expect(guide?.title).toContain('legacy Axon Local');
    expect(guide?.actions.map((action) => action.id)).toEqual([
      'open-connectors',
      'show-terminal',
      'switch-to-ide',
    ]);
  });

  it('prioritizes required connector guidance when idle and probes are down', () => {
    const guide = buildOperatorQuickGuide({
      ...base,
      runPhase: null,
      hasActiveRun: false,
      terminalVisible: true,
      requiredConnectorsUnavailable: 2,
    });

    expect(guide?.tone).toBe('attention');
    expect(guide?.title).toContain('2 required connectors down');
    expect(guide?.steps.join(' ')).toContain('Reprobe');
    expect(guide?.actions.map((action) => action.id)).toEqual(['open-connectors', 'switch-to-ide']);
  });

  it('includes terminal reopen when required connectors are down and terminal is hidden', () => {
    const guide = buildOperatorQuickGuide({
      ...base,
      runPhase: null,
      hasActiveRun: false,
      terminalVisible: false,
      requiredConnectorsUnavailable: 1,
    });

    expect(guide?.title).toContain('Required connector down');
    expect(guide?.actions.map((action) => action.id)).toEqual([
      'open-connectors',
      'show-terminal',
      'switch-to-ide',
    ]);
  });

  it('defers required connector guidance while a run is active', () => {
    const guide = buildOperatorQuickGuide({
      ...base,
      runPhase: 'executing',
      hasActiveRun: true,
      requiredConnectorsUnavailable: 1,
    });

    expect(guide?.title).toContain('Run in progress');
  });

  it('surfaces approval actions when approvals are pending', () => {
    const guide = buildOperatorQuickGuide({
      ...base,
      runPhase: 'executing',
      hasActiveRun: true,
      pendingApprovals: 1,
    });

    expect(guide?.tone).toBe('attention');
    expect(guide?.actions.map((action) => action.id)).toEqual(['open-attention', 'open-briefing']);
  });

  it('returns null in IDE mode', () => {
    expect(
      buildOperatorQuickGuide({
        ...base,
        runPhase: 'review_ready',
        hasActiveRun: true,
        layoutMode: 'ide',
      }),
    ).toBeNull();
  });
});
