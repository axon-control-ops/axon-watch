import { describe, expect, it } from 'vitest';

import { buildOperatorQuickGuide } from './operator-quick-guide';

describe('buildOperatorQuickGuide', () => {
  it('returns review_ready guidance in operator mode', () => {
    const guide = buildOperatorQuickGuide({
      runPhase: 'review_ready',
      hasActiveRun: true,
      pendingApprovals: 0,
      layoutMode: 'operator',
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
    });

    expect(guide?.steps.join(' ')).toContain('git status');
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
