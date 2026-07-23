import { onBeforeUnmount, watch, type WatchStopHandle } from 'vue';

import { clearKairoVoiceFollowupWindow, kairoVoiceFollowupExpiresAt } from '../../lib/kairo-voice-followup-window';
import { isKairoVoiceSpeaking } from '../../lib/kairo-voice-playback';
import { logKairoVoice } from '../../lib/kairo-voice-debug';
import { recordVoiceLoopDiagnostic } from '../../lib/kairo-voice-loop-diagnostics';
import {
  canStartKairoSpeechCapture,
  kairoCaptureCapturing,
  kairoCaptureError,
  registerKairoCaptureEndListener,
  startKairoSpeechCapture,
  stopKairoSpeechCapture,
} from './kairo-shared-speech-capture';
import { kairoConversationPhase } from './kairo-conversation-state';
import {
  resolveHandsFreeCaptureEnd,
  resolveHandsFreeRestartTick,
  resolveHandsFreeSync,
  type HandsFreeLoopDecision,
} from './kairo-hands-free-loop-policy';

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

  function applyDecision(decision: HandsFreeLoopDecision): void {
    recordVoiceLoopDiagnostic({
      kind: 'hands_free_decision',
      action: decision.action,
      reason: decision.reason,
      delayMs: 'delayMs' in decision ? decision.delayMs : undefined,
      failures: consecutiveStartFailures,
    });
    logKairoVoice('hands_free_decision', {
      action: decision.action,
      reason: decision.reason,
      failures: consecutiveStartFailures,
    });

    if (decision.action === 'stop_all') {
      clearRestartTimer();
      clearKairoVoiceFollowupWindow();
      consecutiveStartFailures = 0;
      if (kairoCaptureCapturing.value) {
        stopKairoSpeechCapture();
      }
      wasVoiceOutputActive = false;
      return;
    }

    if (decision.action === 'hold') {
      clearRestartTimer();
      if (decision.reason === 'conversation_pending' && kairoCaptureCapturing.value) {
        stopKairoSpeechCapture();
      }
      return;
    }

    if (decision.action === 'start_barge_in') {
      wasVoiceOutputActive = true;
      clearRestartTimer();
      if (!kairoCaptureCapturing.value) {
        startKairoSpeechCapture('barge_in');
      }
      return;
    }

    if (decision.incrementFailure) {
      consecutiveStartFailures += 1;
    } else if (decision.reason === 'ambient_end' || decision.reason === 'post_speech') {
      consecutiveStartFailures = 0;
    }

    if (decision.delayMs <= 0) {
      const started = startKairoSpeechCapture('hands_free');
      if (!started) {
        consecutiveStartFailures += 1;
        scheduleRestartFromPolicy(
          resolveHandsFreeRestartTick({
            enabled: options.enabled(),
            privacyBlocked: options.privacyBlocked(),
            conversationPending: options.conversationPending(),
            capturing: kairoCaptureCapturing.value,
            voiceOutputActive: isVoiceOutputActive(),
            canStartCapture: false,
            consecutiveStartFailures,
          }),
        );
        return;
      }
      consecutiveStartFailures = 0;
      return;
    }

    scheduleRestartFromPolicy(decision);
  }

  function scheduleRestartFromPolicy(decision: HandsFreeLoopDecision): void {
    if (decision.action !== 'schedule_restart') {
      applyDecision(decision);
      return;
    }
    clearRestartTimer();
    if (!options.enabled() || options.privacyBlocked()) {
      return;
    }
    const delayMs = decision.delayMs;
    restartTimer = window.setTimeout(() => {
      const tick = resolveHandsFreeRestartTick({
        enabled: options.enabled(),
        privacyBlocked: options.privacyBlocked(),
        conversationPending: options.conversationPending(),
        capturing: kairoCaptureCapturing.value,
        voiceOutputActive: isVoiceOutputActive(),
        canStartCapture: canStartKairoSpeechCapture(),
        consecutiveStartFailures,
      });
      if (tick.action === 'schedule_restart' && tick.delayMs === 0 && !tick.incrementFailure) {
        const started = startKairoSpeechCapture('hands_free');
        if (!started) {
          consecutiveStartFailures += 1;
          applyDecision(
            resolveHandsFreeRestartTick({
              enabled: options.enabled(),
              privacyBlocked: options.privacyBlocked(),
              conversationPending: options.conversationPending(),
              capturing: kairoCaptureCapturing.value,
              voiceOutputActive: isVoiceOutputActive(),
              canStartCapture: false,
              consecutiveStartFailures,
            }),
          );
          return;
        }
        consecutiveStartFailures = 0;
        return;
      }
      applyDecision(tick);
    }, delayMs);
  }

  function syncHandsFreeState(): void {
    const voiceOut = isVoiceOutputActive();
    const decision = resolveHandsFreeSync({
      enabled: options.enabled(),
      privacyBlocked: options.privacyBlocked(),
      conversationPending: options.conversationPending(),
      voiceOutputActive: voiceOut,
      capturing: kairoCaptureCapturing.value,
      consecutiveStartFailures,
      wasVoiceOutputActive,
    });
    if (decision.action === 'schedule_restart' && !voiceOut) {
      wasVoiceOutputActive = false;
    }
    applyDecision(decision);
  }

  const unregisterCaptureEnd = registerKairoCaptureEndListener(() => {
    const decision = resolveHandsFreeCaptureEnd({
      enabled: options.enabled(),
      voiceOutputActive: isVoiceOutputActive(),
      captureError: Boolean(kairoCaptureError.value),
      consecutiveStartFailures,
      wasVoiceOutputActive,
    });
    if (!decision) {
      return;
    }
    applyDecision(decision);
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
