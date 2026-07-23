/**
 * Pure policy for the hands-free restart / barge-in loop.
 * Kept framework-free so Vitest can cover transitions without Vue.
 */

export const HANDS_FREE_RESTART_DELAY_MS = 280;
export const HANDS_FREE_POST_SPEECH_COOLDOWN_MS = 700;
/** After a clean ambient end (Chromium no-speech), wait longer before restart to cut thrash. */
export const HANDS_FREE_AMBIENT_RESTART_MS = 1600;
export const HANDS_FREE_FAIL_BACKOFF_MS = [1200, 3000, 8000, 15000] as const;

export type HandsFreeRestartReason =
  | 'privacy_or_disabled'
  | 'conversation_pending'
  | 'voice_output_barge_in'
  | 'capture_already_active'
  | 'start_failed'
  | 'capture_error'
  | 'ambient_end'
  | 'post_speech'
  | 'initial_arm';

export type HandsFreeLoopDecision =
  | { action: 'stop_all'; reason: HandsFreeRestartReason }
  | { action: 'hold'; reason: HandsFreeRestartReason }
  | { action: 'start_barge_in'; reason: HandsFreeRestartReason }
  | {
      action: 'schedule_restart';
      reason: HandsFreeRestartReason;
      delayMs: number;
      incrementFailure: boolean;
    };

export function nextHandsFreeFailDelayMs(consecutiveStartFailures: number): number {
  const index = Math.min(
    Math.max(0, consecutiveStartFailures),
    HANDS_FREE_FAIL_BACKOFF_MS.length - 1,
  );
  return HANDS_FREE_FAIL_BACKOFF_MS[index] ?? 15000;
}

export function resolveHandsFreeSync(input: {
  enabled: boolean;
  privacyBlocked: boolean;
  conversationPending: boolean;
  voiceOutputActive: boolean;
  capturing: boolean;
  consecutiveStartFailures: number;
  wasVoiceOutputActive: boolean;
}): HandsFreeLoopDecision {
  if (!input.enabled || input.privacyBlocked) {
    return { action: 'stop_all', reason: 'privacy_or_disabled' };
  }
  if (input.conversationPending) {
    return { action: 'hold', reason: 'conversation_pending' };
  }
  if (input.voiceOutputActive) {
    return { action: 'start_barge_in', reason: 'voice_output_barge_in' };
  }
  if (input.capturing) {
    return { action: 'hold', reason: 'capture_already_active' };
  }
  const delay =
    input.consecutiveStartFailures > 0
      ? nextHandsFreeFailDelayMs(input.consecutiveStartFailures)
      : input.wasVoiceOutputActive
        ? HANDS_FREE_POST_SPEECH_COOLDOWN_MS
        : HANDS_FREE_RESTART_DELAY_MS;
  return {
    action: 'schedule_restart',
    reason: input.wasVoiceOutputActive ? 'post_speech' : 'initial_arm',
    delayMs: delay,
    incrementFailure: false,
  };
}

export function resolveHandsFreeCaptureEnd(input: {
  enabled: boolean;
  voiceOutputActive: boolean;
  captureError: boolean;
  consecutiveStartFailures: number;
  wasVoiceOutputActive: boolean;
}): HandsFreeLoopDecision | null {
  if (!input.enabled || input.voiceOutputActive) {
    return null;
  }
  if (input.captureError) {
    return {
      action: 'schedule_restart',
      reason: 'capture_error',
      delayMs: nextHandsFreeFailDelayMs(input.consecutiveStartFailures),
      incrementFailure: true,
    };
  }
  return {
    action: 'schedule_restart',
    reason: input.wasVoiceOutputActive ? 'post_speech' : 'ambient_end',
    delayMs: input.wasVoiceOutputActive
      ? HANDS_FREE_POST_SPEECH_COOLDOWN_MS
      : HANDS_FREE_AMBIENT_RESTART_MS,
    incrementFailure: false,
  };
}

export function resolveHandsFreeRestartTick(input: {
  enabled: boolean;
  privacyBlocked: boolean;
  conversationPending: boolean;
  capturing: boolean;
  voiceOutputActive: boolean;
  canStartCapture: boolean;
  consecutiveStartFailures: number;
}): HandsFreeLoopDecision {
  if (
    !input.enabled ||
    input.privacyBlocked ||
    input.conversationPending ||
    input.capturing ||
    input.voiceOutputActive
  ) {
    return { action: 'hold', reason: 'conversation_pending' };
  }
  if (!input.canStartCapture) {
    return {
      action: 'schedule_restart',
      reason: 'start_failed',
      delayMs: nextHandsFreeFailDelayMs(input.consecutiveStartFailures),
      incrementFailure: true,
    };
  }
  return {
    action: 'schedule_restart',
    reason: 'initial_arm',
    delayMs: 0,
    incrementFailure: false,
  };
}
