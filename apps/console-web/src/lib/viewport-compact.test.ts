import { describe, expect, it } from 'vitest';

import type { OperatorPresence } from '../contracts/canonical';

import { defaultOperatorPresenceSettings } from './operator-presence-settings';

import {
  MOBILE_COMPACT_BREAKPOINT,
  shouldRequestViewportCompactBriefing,
  shouldUseMobileCompactLayout,
} from './viewport-compact';

const presence: OperatorPresence = {
  persona_voice_line: 'KAIRO: ready',
  presence_state: 'observing' as const,
  settings: {
    ...defaultOperatorPresenceSettings(),
    mobile_compact_preferred: true,
    stt_mode: 'browser',
  },
  spoken_alert: {
    eligible: false,
    reason: 'no_interruptive_signal',
    signal_id: null,
    message: '',
  },
  mobile: { compact_layout: false, foreground_only: true },
};

describe('viewport compact helpers', () => {
  it('requests compact briefing below the breakpoint', () => {
    expect(shouldRequestViewportCompactBriefing(767, presence)).toBe(true);
    expect(shouldRequestViewportCompactBriefing(768, presence)).toBe(false);
  });

  it('uses server compact_layout flag immediately', () => {
    expect(
      shouldUseMobileCompactLayout(1200, {
        ...presence,
        mobile: { compact_layout: true, foreground_only: true },
      }),
    ).toBe(true);
  });

  it('reacts to viewport width without server flag', () => {
    expect(shouldUseMobileCompactLayout(640, presence)).toBe(true);
    expect(shouldUseMobileCompactLayout(1024, presence)).toBe(false);
  });

  it('respects disabled mobile compact preference', () => {
    expect(
      shouldRequestViewportCompactBriefing(640, presence, {
        ...presence.settings,
        mobile_compact_preferred: false,
      }),
    ).toBe(false);
  });

  it('documents the locked breakpoint', () => {
    expect(MOBILE_COMPACT_BREAKPOINT).toBe(768);
  });
});
