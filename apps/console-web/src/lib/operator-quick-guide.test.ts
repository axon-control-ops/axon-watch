import { describe, expect, it } from 'vitest';

import { buildOperatorQuickGuide } from './operator-quick-guide';

describe('buildOperatorQuickGuide', () => {
  it('returns review_ready guidance in operator mode', () => {
    const guide = buildOperatorQuickGuide({
      runPhase: 'review_ready',
      hasActiveRun: true,
      pendingApprovals: 0,
      layoutMode: 'operator',
      terminalVisible: true,
    });

    expect(guide?.title).toContain('Review ready');
    expect(guide?.tone).toBe('attention');
    expect(guide?.steps.join(' ')).toContain('COMPLETE RUN');
    expect(guide?.steps.join(' ')).toContain('multi-step');
    expect(guide?.actions.some((action) => action.id === 'switch-to-ide')).toBe(true);
  });

  it('returns idle guidance when no run is active', () => {
    const guide = buildOperatorQuickGuide({
      runPhase: null,
      hasActiveRun: false,
      pendingApprovals: 0,
      layoutMode: 'operator',
      terminalVisible: true,
    });

    expect(guide?.steps.join(' ')).toContain('git status');
    expect(guide?.actions).toEqual([{ id: 'switch-to-ide', label: 'Switch to IDE' }]);
  });

  it('surfaces terminal reopen paths when the panel is hidden', () => {
    const idle = buildOperatorQuickGuide({
      runPhase: null,
      hasActiveRun: false,
      pendingApprovals: 0,
      layoutMode: 'operator',
      terminalVisible: false,
    });
    expect(idle?.title).toContain('Terminal hidden');
    expect(idle?.steps.join(' ')).toContain('Ctrl/Cmd+J');
    expect(idle?.actions.some((action) => action.id === 'show-terminal')).toBe(true);

    const executing = buildOperatorQuickGuide({
      runPhase: 'executing',
      hasActiveRun: true,
      pendingApprovals: 0,
      layoutMode: 'operator',
      terminalVisible: false,
    });
    expect(executing?.title).toContain('open the terminal');
    expect(executing?.tone).toBe('attention');
    expect(executing?.steps[0]).toContain('Ctrl/Cmd+J');
  });

  it('surfaces required connector attention with an Open connectors action', () => {
    const guide = buildOperatorQuickGuide({
      runPhase: null,
      hasActiveRun: false,
      pendingApprovals: 0,
      layoutMode: 'operator',
      terminalVisible: true,
      requiredConnectorsUnavailable: 2,
    });

    expect(guide?.tone).toBe('attention');
    expect(guide?.title).toContain('2 required connectors down');
    expect(guide?.actions[0]).toEqual({ id: 'open-connectors', label: 'Open connectors' });
  });

  it('surfaces watch offline guidance instead of stale connector counts', () => {
    const guide = buildOperatorQuickGuide({
      runPhase: null,
      hasActiveRun: false,
      pendingApprovals: 0,
      layoutMode: 'operator',
      terminalVisible: true,
      watchConnected: false,
      requiredConnectorsUnavailable: 2,
    });

    expect(guide?.tone).toBe('attention');
    expect(guide?.title).toContain('Watch offline');
    expect(guide?.steps.join(' ')).toContain('connector probes paused');
    expect(guide?.actions[0]).toEqual({ id: 'open-connectors', label: 'Open connectors' });
  });

  it('surfaces terminal reopen paths when the panel is hidden', () => {
    const idle = buildOperatorQuickGuide({
      runPhase: null,
      hasActiveRun: false,
      pendingApprovals: 0,
      layoutMode: 'operator',
      terminalVisible: false,
    });
    expect(idle?.title).toContain('Terminal hidden');
    expect(idle?.steps.join(' ')).toContain('Ctrl/Cmd+J');
    expect(idle?.steps.join(' ')).toContain('Open terminal');

    const executing = buildOperatorQuickGuide({
      runPhase: 'executing',
      hasActiveRun: true,
      pendingApprovals: 0,
      layoutMode: 'operator',
      terminalVisible: false,
    });
    expect(executing?.title).toContain('open the terminal');
    expect(executing?.steps[0]).toContain('Ctrl/Cmd+J');
  });

  it('returns null in IDE mode', () => {
    expect(
      buildOperatorQuickGuide({
        runPhase: 'review_ready',
        hasActiveRun: true,
        pendingApprovals: 0,
        layoutMode: 'ide',
        terminalVisible: true,
      }),
    ).toBeNull();
  });
});
