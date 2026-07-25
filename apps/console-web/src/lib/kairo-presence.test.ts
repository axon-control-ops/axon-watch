import { describe, expect, it } from 'vitest';

import { kairoPresenceLabel, resolveKairoPresenceState } from './kairo-presence';

describe('resolveKairoPresenceState', () => {
  it('returns privacy_blocked when privacy mode blocks presence', () => {
    expect(
      resolveKairoPresenceState({
        privacyBlocked: true,
        pendingApprovals: 2,
        criticalSignals: 1,
        highSignals: 0,
        watchConnected: true,
        runtimeLoaded: true,
      }),
    ).toBe('privacy_blocked');
  });

  it('returns alerting when approvals or high-severity signals exist', () => {
    expect(
      resolveKairoPresenceState({
        pendingApprovals: 1,
        criticalSignals: 0,
        highSignals: 0,
        watchConnected: true,
        runtimeLoaded: true,
      }),
    ).toBe('alerting');
  });

  it('returns observing when runtime is loaded and watch is connected', () => {
    expect(
      resolveKairoPresenceState({
        pendingApprovals: 0,
        criticalSignals: 0,
        highSignals: 0,
        watchConnected: true,
        runtimeLoaded: true,
      }),
    ).toBe('observing');
  });
});

describe('kairoPresenceLabel', () => {
  it('maps states to operator-facing labels', () => {
    expect(kairoPresenceLabel('observing')).toBe('VAXON · observing');
    expect(kairoPresenceLabel('thinking')).toBe('VAXON · checking');
    expect(kairoPresenceLabel('alerting')).toBe('VAXON · attention');
  });
});
