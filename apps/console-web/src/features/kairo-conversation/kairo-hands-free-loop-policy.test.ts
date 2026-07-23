import { describe, expect, it } from 'vitest';

import {
  HANDS_FREE_AMBIENT_RESTART_MS,
  HANDS_FREE_FAIL_BACKOFF_MS,
  HANDS_FREE_POST_SPEECH_COOLDOWN_MS,
  HANDS_FREE_RESTART_DELAY_MS,
  nextHandsFreeFailDelayMs,
  resolveHandsFreeCaptureEnd,
  resolveHandsFreeRestartTick,
  resolveHandsFreeSync,
} from './kairo-hands-free-loop-policy';

describe('kairo-hands-free-loop-policy', () => {
  it('stops everything when privacy or disabled', () => {
    expect(
      resolveHandsFreeSync({
        enabled: true,
        privacyBlocked: true,
        conversationPending: false,
        voiceOutputActive: false,
        capturing: true,
        consecutiveStartFailures: 0,
        wasVoiceOutputActive: false,
      }),
    ).toEqual({ action: 'stop_all', reason: 'privacy_or_disabled' });
  });

  it('holds while a converse turn is pending', () => {
    expect(
      resolveHandsFreeSync({
        enabled: true,
        privacyBlocked: false,
        conversationPending: true,
        voiceOutputActive: false,
        capturing: false,
        consecutiveStartFailures: 0,
        wasVoiceOutputActive: false,
      }).action,
    ).toBe('hold');
  });

  it('starts barge-in while voice output is active', () => {
    expect(
      resolveHandsFreeSync({
        enabled: true,
        privacyBlocked: false,
        conversationPending: false,
        voiceOutputActive: true,
        capturing: false,
        consecutiveStartFailures: 0,
        wasVoiceOutputActive: false,
      }),
    ).toEqual({ action: 'start_barge_in', reason: 'voice_output_barge_in' });
  });

  it('uses post-speech cooldown after TTS', () => {
    const decision = resolveHandsFreeSync({
      enabled: true,
      privacyBlocked: false,
      conversationPending: false,
      voiceOutputActive: false,
      capturing: false,
      consecutiveStartFailures: 0,
      wasVoiceOutputActive: true,
    });
    expect(decision).toMatchObject({
      action: 'schedule_restart',
      reason: 'post_speech',
      delayMs: HANDS_FREE_POST_SPEECH_COOLDOWN_MS,
    });
  });

  it('uses ambient restart after clean capture end', () => {
    const decision = resolveHandsFreeCaptureEnd({
      enabled: true,
      voiceOutputActive: false,
      captureError: false,
      consecutiveStartFailures: 0,
      wasVoiceOutputActive: false,
    });
    expect(decision).toMatchObject({
      action: 'schedule_restart',
      reason: 'ambient_end',
      delayMs: HANDS_FREE_AMBIENT_RESTART_MS,
      incrementFailure: false,
    });
  });

  it('backs off on capture errors', () => {
    expect(nextHandsFreeFailDelayMs(0)).toBe(HANDS_FREE_FAIL_BACKOFF_MS[0]);
    expect(nextHandsFreeFailDelayMs(99)).toBe(15000);
    const decision = resolveHandsFreeCaptureEnd({
      enabled: true,
      voiceOutputActive: false,
      captureError: true,
      consecutiveStartFailures: 1,
      wasVoiceOutputActive: false,
    });
    expect(decision).toMatchObject({
      action: 'schedule_restart',
      reason: 'capture_error',
      incrementFailure: true,
      delayMs: HANDS_FREE_FAIL_BACKOFF_MS[1],
    });
  });

  it('arms with the short initial delay when idle', () => {
    const decision = resolveHandsFreeSync({
      enabled: true,
      privacyBlocked: false,
      conversationPending: false,
      voiceOutputActive: false,
      capturing: false,
      consecutiveStartFailures: 0,
      wasVoiceOutputActive: false,
    });
    expect(decision).toMatchObject({
      action: 'schedule_restart',
      delayMs: HANDS_FREE_RESTART_DELAY_MS,
    });
  });

  it('retries when capture cannot start', () => {
    const decision = resolveHandsFreeRestartTick({
      enabled: true,
      privacyBlocked: false,
      conversationPending: false,
      capturing: false,
      voiceOutputActive: false,
      canStartCapture: false,
      consecutiveStartFailures: 0,
    });
    expect(decision).toMatchObject({
      action: 'schedule_restart',
      reason: 'start_failed',
      incrementFailure: true,
    });
  });
});
