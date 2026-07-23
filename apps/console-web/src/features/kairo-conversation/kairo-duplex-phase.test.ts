import { describe, expect, it } from 'vitest';

import {
  bargeInDuckGain,
  DUPLEX_FOLLOWUP_WINDOW_MS,
  mapLegacyPhaseToDuplex,
  shouldRejectSpeakerBleed,
} from './kairo-duplex-phase';

describe('kairo-duplex-phase', () => {
  it('keeps the follow-up window as an explicit 30s policy value', () => {
    expect(DUPLEX_FOLLOWUP_WINDOW_MS).toBe(30_000);
  });

  it('maps listening + follow-up to followup_ready', () => {
    expect(mapLegacyPhaseToDuplex('listening', { followupActive: true })).toBe('followup_ready');
    expect(mapLegacyPhaseToDuplex('idle', { privacyMuted: true })).toBe('privacy_muted');
  });

  it('ducks TTS during barge-in', () => {
    expect(bargeInDuckGain(true)).toBeLessThan(0.25);
    expect(bargeInDuckGain(false)).toBe(1);
  });

  it('rejects obvious speaker-bleed echoes', () => {
    expect(
      shouldRejectSpeakerBleed({
        transcript: 'Nothing urgent from my scan',
        lastSpokenReply: 'Nothing urgent from my scan — what shall we tackle?',
      }),
    ).toBe(true);
    expect(
      shouldRejectSpeakerBleed({
        transcript: 'show git status please',
        lastSpokenReply: 'Nothing urgent from my scan — what shall we tackle?',
      }),
    ).toBe(false);
  });
});
