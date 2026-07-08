import { describe, expect, it } from 'vitest';

import {
  dockHeroModeLabel,
  dockHeroModeTitle,
  resolveDefaultDockHeroMode,
} from './dock-hero-mode';

describe('dock-hero-mode', () => {
  it('defaults to command when no attention signals', () => {
    expect(
      resolveDefaultDockHeroMode({
        pendingApprovals: 0,
        criticalSignals: 0,
        highSignals: 0,
      }),
    ).toBe('command');
  });

  it('defaults to briefing when approvals or high-severity signals need attention', () => {
    expect(
      resolveDefaultDockHeroMode({
        pendingApprovals: 1,
        criticalSignals: 0,
        highSignals: 0,
      }),
    ).toBe('briefing');

    expect(
      resolveDefaultDockHeroMode({
        pendingApprovals: 0,
        criticalSignals: 0,
        highSignals: 2,
      }),
    ).toBe('briefing');
  });

  it('derives operator-facing labels', () => {
    expect(dockHeroModeLabel('command')).toBe('Command');
    expect(dockHeroModeTitle('command')).toBe('Command');
    expect(dockHeroModeTitle('briefing')).toBe('VAXON Briefing');
  });
});
