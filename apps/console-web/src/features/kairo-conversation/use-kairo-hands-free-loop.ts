import { onBeforeUnmount, watch, type WatchStopHandle } from 'vue';

import { clearKairoVoiceFollowupWindow } from '../../lib/kairo-voice-followup-window';
import { isKairoVoiceSpeaking } from '../../lib/kairo-voice-playback';
import {
  canStartKairoSpeechCapture,
  kairoCaptureCapturing,
  kairoCaptureMode,
  registerKairoCaptureEndListener,
  startKairoSpeechCapture,
  stopKairoSpeechCapture,
} from './kairo-shared-speech-capture';
import { kairoConversationPhase } from './kairo-conversation-state';

const RESTART_DELAY_MS = 280;
const POST_SPEECH_COOLDOWN_MS = 700;

export function useKairoHandsFreeLoop(options: {
  enabled: () => boolean;
  privacyBlocked: () => boolean;
  kairoSpeaking: () => boolean;
  conversationPending: () => boolean;
}): void {
  let restartTimer: number | null = null;
  let stopWatch: WatchStopHandle | null = null;
  let wasVoiceOutputActive = false;

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

  function scheduleRestart(delayMs = RESTART_DELAY_MS): void {
    clearRestartTimer();
    if (!options.enabled() || options.privacyBlocked()) {
      return;
    }
    restartTimer = window.setTimeout(() => {
      if (
        !options.enabled() ||
        options.privacyBlocked() ||
        options.conversationPending() ||
        kairoCaptureCapturing.value ||
        isVoiceOutputActive()
      ) {
        return;
      }
      if (!canStartKairoSpeechCapture()) {
        return;
      }
      startKairoSpeechCapture('hands_free');
    }, delayMs);
  }

  function syncHandsFreeState(): void {
    if (!options.enabled() || options.privacyBlocked()) {
      clearRestartTimer();
      clearKairoVoiceFollowupWindow();
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

    if (isVoiceOutputActive()) {
      wasVoiceOutputActive = true;
      clearRestartTimer();
      if (kairoCaptureCapturing.value) {
        stopKairoSpeechCapture();
      }
      return;
    }

    if (!kairoCaptureCapturing.value) {
      const delay = wasVoiceOutputActive ? POST_SPEECH_COOLDOWN_MS : RESTART_DELAY_MS;
      wasVoiceOutputActive = false;
      scheduleRestart(delay);
    }
  }

  const unregisterCaptureEnd = registerKairoCaptureEndListener(() => {
    if (!options.enabled() || isVoiceOutputActive()) {
      return;
    }
    scheduleRestart(wasVoiceOutputActive ? POST_SPEECH_COOLDOWN_MS : RESTART_DELAY_MS);
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
