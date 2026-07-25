import { onBeforeUnmount, watch, type WatchStopHandle } from 'vue';

import { clearKairoVoiceFollowupWindow, kairoVoiceFollowupExpiresAt } from '../../lib/kairo-voice-followup-window';
import { isKairoVoiceSpeaking } from '../../lib/kairo-voice-playback';
import {
  canStartKairoSpeechCapture,
  kairoCaptureCapturing,
  kairoCaptureError,
  registerKairoCaptureEndListener,
  startKairoSpeechCapture,
  stopKairoSpeechCapture,
} from './kairo-shared-speech-capture';
import { kairoConversationPhase } from './kairo-conversation-state';

const RESTART_DELAY_MS = 280;
const POST_SPEECH_COOLDOWN_MS = 700;
/** After a clean ambient end (Chromium no-speech), wait longer before restart to cut thrash. */
const AMBIENT_RESTART_MS = 1600;
const FAIL_BACKOFF_MS = [1200, 3000, 8000, 15000] as const;

export function useKairoHandsFreeLoop(options: {
  enabled: () => boolean;
  privacyBlocked: () => boolean;
  kairoSpeaking: () => boolean;
  conversationPending: () => boolean;
}): void {
  let restartTimer: number | null = null;
  let stopWatch: WatchStopHandle | null = null;
  let wasVoiceOutputActive = false;
  let consecutiveStartFailures = 0;

  function clearRestartTimer(): void {
    if (restartTimer !== null) {
      window.clearTimeout(restartTimer);
      restartTimer = null;
    }
  }

  function isVoiceOutputActive(): boolean {
    return (
      options.kairoSpeaking() ||
      isKairoVoiceSpeaking() ||
      kairoConversationPhase.value === 'speaking' ||
      kairoConversationPhase.value === 'thinking'
    );
  }

  function nextFailDelayMs(): number {
    const index = Math.min(consecutiveStartFailures, FAIL_BACKOFF_MS.length - 1);
    return FAIL_BACKOFF_MS[index] ?? 15000;
  }

  function scheduleRestart(delayMs = RESTART_DELAY_MS): void {
    clearRestartTimer();
    if (!options.enabled() || options.privacyBlocked()) {
      return;
    }
    restartTimer = window.setTimeout(() => {
      const blocked =
        !options.enabled() ||
        options.privacyBlocked() ||
        options.conversationPending() ||
        kairoCaptureCapturing.value ||
        isVoiceOutputActive();
      if (blocked) {
        return;
      }
      if (!canStartKairoSpeechCapture()) {
        consecutiveStartFailures += 1;
        scheduleRestart(nextFailDelayMs());
        return;
      }
      const started = startKairoSpeechCapture('hands_free');
      if (!started) {
        consecutiveStartFailures += 1;
        scheduleRestart(nextFailDelayMs());
        return;
      }
      consecutiveStartFailures = 0;
    }, delayMs);
  }

  function syncHandsFreeState(): void {
    const voiceOut = isVoiceOutputActive();
    if (!options.enabled() || options.privacyBlocked()) {
      clearRestartTimer();
      clearKairoVoiceFollowupWindow();
      consecutiveStartFailures = 0;
      if (kairoCaptureCapturing.value) {
        stopKairoSpeechCapture();
      }
      wasVoiceOutputActive = false;
      return;
    }

    if (options.conversationPending()) {
      clearRestartTimer();
      if (kairoCaptureCapturing.value) {
        stopKairoSpeechCapture();
      }
      return;
    }

    if (voiceOut) {
      wasVoiceOutputActive = true;
      clearRestartTimer();
      // Keep a lightweight barge-in capture alive during TTS so stop/wake works.
      if (!kairoCaptureCapturing.value) {
        startKairoSpeechCapture('barge_in');
      }
      return;
    }

    if (!kairoCaptureCapturing.value) {
      const delay =
        consecutiveStartFailures > 0
          ? nextFailDelayMs()
          : wasVoiceOutputActive
            ? POST_SPEECH_COOLDOWN_MS
            : RESTART_DELAY_MS;
      wasVoiceOutputActive = false;
      scheduleRestart(delay);
    }
  }

  const unregisterCaptureEnd = registerKairoCaptureEndListener(() => {
    if (!options.enabled() || isVoiceOutputActive()) {
      return;
    }
    if (kairoCaptureError.value) {
      consecutiveStartFailures += 1;
      scheduleRestart(nextFailDelayMs());
      return;
    }
    consecutiveStartFailures = 0;
    scheduleRestart(
      wasVoiceOutputActive ? POST_SPEECH_COOLDOWN_MS : AMBIENT_RESTART_MS,
    );
  });

  stopWatch = watch(
    () =>
      [
        options.enabled(),
        options.privacyBlocked(),
        options.kairoSpeaking(),
        options.conversationPending(),
        kairoConversationPhase.value,
        kairoCaptureCapturing.value,
        // Re-arm mic when a follow-up window opens after unsolicited speech.
        kairoVoiceFollowupExpiresAt.value,
      ] as const,
    () => {
      syncHandsFreeState();
    },
    { immediate: true },
  );

  onBeforeUnmount(() => {
    clearRestartTimer();
    stopWatch?.();
    unregisterCaptureEnd();
  });
}
