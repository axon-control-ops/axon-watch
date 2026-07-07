import { describe, expect, it } from 'vitest';

import {
  ideConversationalVoiceEnabled,
  ideVoiceSpeechAllowed,
  ideVoiceStripStatusLabel,
  shouldShowIdeVoiceStrip,
} from './ide-voice-strip';

describe('ide voice strip', () => {
  it('shows in IDE when conversational narration is enabled', () => {
    expect(
      shouldShowIdeVoiceStrip({
        layoutMode: 'ide',
        settings: {
          ide_voice_strip_enabled: false,
          kairo_narration: 'conversational',
          privacy_mode: false,
        },
        foundationSurface: false,
      }),
    ).toBe(true);
    expect(
      shouldShowIdeVoiceStrip({
        layoutMode: 'ide',
        settings: {
          ide_voice_strip_enabled: false,
          kairo_narration: 'off',
          privacy_mode: false,
        },
        foundationSurface: false,
      }),
    ).toBe(false);
    expect(
      shouldShowIdeVoiceStrip({
        layoutMode: 'operator',
        settings: {
          ide_voice_strip_enabled: true,
          kairo_narration: 'conversational',
          privacy_mode: false,
        },
        foundationSurface: false,
      }),
    ).toBe(false);
  });

  it('allows IDE speech when conversational narration is enabled', () => {
    expect(
      ideVoiceSpeechAllowed({
        layoutMode: 'ide',
        settings: {
          ide_voice_strip_enabled: false,
          kairo_narration: 'conversational',
          privacy_mode: false,
        },
      }),
    ).toBe(true);
    expect(
      ideVoiceSpeechAllowed({
        layoutMode: 'operator',
        settings: {
          ide_voice_strip_enabled: false,
          kairo_narration: 'conversational',
          privacy_mode: false,
        },
      }),
    ).toBe(true);
  });

  it('labels speaking and interrupt hint states', () => {
    expect(
      ideVoiceStripStatusLabel({
        speaking: true,
        narration: 'conversational',
        liveLine: null,
      }),
    ).toContain('interrupt');
    expect(ideConversationalVoiceEnabled({ kairo_narration: 'off', privacy_mode: false })).toBe(
      false,
    );
  });
});
