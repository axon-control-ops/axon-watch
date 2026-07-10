import { describe, expect, it } from 'vitest';

import { resolveKairoPresenceClickTarget } from './kairo-presence-action';

describe('resolveKairoPresenceClickTarget', () => {
  it('routes alerting to Attention', () => {
    expect(
      resolveKairoPresenceClickTarget({
        paused: false,
        voiceBusy: false,
        layoutMode: 'ide',
        state: 'alerting',
      }),
    ).toBe('attention');
  });

  it('pauses busy voice in IDE', () => {
    expect(
      resolveKairoPresenceClickTarget({
        paused: false,
        voiceBusy: true,
        layoutMode: 'ide',
        state: 'speaking',
      }),
    ).toBe('pause');
  });

  it('opens briefing for idle presence', () => {
    expect(
      resolveKairoPresenceClickTarget({
        paused: false,
        voiceBusy: false,
        layoutMode: 'operator',
        state: 'idle',
      }),
    ).toBe('briefing');
  });
});
