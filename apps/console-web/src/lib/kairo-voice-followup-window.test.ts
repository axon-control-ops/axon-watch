import { afterEach, describe, expect, it, vi } from 'vitest';

import {
  clearKairoVoiceFollowupWindow,
  finalizeKairoVoiceFollowupWindow,
  isKairoVoiceFollowupWindowActive,
  KAIRO_VOICE_FOLLOWUP_WINDOW_MS,
  kairoVoiceFollowupRemainingMs,
  openKairoVoiceFollowupWindow,
  scheduleKairoVoiceFollowupWindowAfterSpeech,
} from './kairo-voice-followup-window';

vi.mock('./kairo-voice-playback', () => ({
  isKairoVoiceSpeaking: vi.fn(() => false),
  onKairoVoiceIdle: vi.fn(() => () => {}),
}));

afterEach(() => {
  clearKairoVoiceFollowupWindow();
});

describe('kairo voice follow-up window', () => {
  it('opens and expires after the configured duration', () => {
    const now = 1_000_000;
    openKairoVoiceFollowupWindow(now);
    expect(isKairoVoiceFollowupWindowActive(now)).toBe(true);
    expect(isKairoVoiceFollowupWindowActive(now + KAIRO_VOICE_FOLLOWUP_WINDOW_MS - 1)).toBe(true);
    expect(isKairoVoiceFollowupWindowActive(now + KAIRO_VOICE_FOLLOWUP_WINDOW_MS)).toBe(false);
    expect(kairoVoiceFollowupRemainingMs(now + 5_000)).toBe(KAIRO_VOICE_FOLLOWUP_WINDOW_MS - 5_000);
  });

  it('finalizes after speech when pending', async () => {
    scheduleKairoVoiceFollowupWindowAfterSpeech();
    expect(isKairoVoiceFollowupWindowActive()).toBe(false);
    finalizeKairoVoiceFollowupWindow();
    expect(isKairoVoiceFollowupWindowActive()).toBe(true);
  });

  it('clears pending and active window', () => {
    openKairoVoiceFollowupWindow();
    scheduleKairoVoiceFollowupWindowAfterSpeech();
    clearKairoVoiceFollowupWindow();
    expect(isKairoVoiceFollowupWindowActive()).toBe(false);
    finalizeKairoVoiceFollowupWindow();
    expect(isKairoVoiceFollowupWindowActive()).toBe(false);
  });
});
