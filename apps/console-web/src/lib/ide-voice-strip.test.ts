import { describe, expect, it } from 'vitest';

import {
  ideVoiceSpeechAllowed,
  ideVoiceStripStatusLabel,
  shouldShowIdeVoiceStrip,
} from './ide-voice-strip';

describe('ide voice strip', () => {
  it('shows only in IDE mode when opt-in is enabled', () => {
    expect(
      shouldShowIdeVoiceStrip({
        layoutMode: 'ide',
        settings: { ide_voice_strip_enabled: true },
        foundationSurface: false,
      }),
    ).toBe(true);
    expect(
      shouldShowIdeVoiceStrip({
        layoutMode: 'ide',
        settings: { ide_voice_strip_enabled: false },
        foundationSurface: false,
      }),
    ).toBe(false);
    expect(
      shouldShowIdeVoiceStrip({
        layoutMode: 'operator',
        settings: { ide_voice_strip_enabled: true },
        foundationSurface: false,
      }),
    ).toBe(false);
  });

  it('gates IDE speech delivery behind the opt-in strip', () => {
    expect(
      ideVoiceSpeechAllowed({
        layoutMode: 'ide',
        settings: { ide_voice_strip_enabled: false, privacy_mode: false },
      }),
    ).toBe(false);
    expect(
      ideVoiceSpeechAllowed({
        layoutMode: 'operator',
        settings: { ide_voice_strip_enabled: false, privacy_mode: false },
      }),
    ).toBe(true);
  });

  it('labels speaking and narration-off states', () => {
    expect(
      ideVoiceStripStatusLabel({
        speaking: true,
        narration: 'conversational',
        liveLine: null,
      }),
    ).toBe('Speaking…');
    expect(
      ideVoiceStripStatusLabel({
        speaking: false,
        narration: 'off',
        liveLine: null,
      }),
    ).toContain('narration off');
  });
});
