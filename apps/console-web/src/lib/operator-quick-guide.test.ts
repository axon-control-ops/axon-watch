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
    expect(guide?.steps.join(' ')).toContain('COMPLETE RUN');
    expect(guide?.steps.join(' ')).toContain('multi-step');
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
      }),
    ).toBeNull();
  });
});
