import { computed, onBeforeUnmount, onMounted, ref, type Ref } from 'vue';

import { resolveOrbPointerUpIntent } from './kairo-galaxy-orb-interaction';
import { subscribeKairoVoiceChunk, subscribeKairoVoiceSpeaking } from '../../lib/kairo-voice-playback';
import type { useKairoSpeechCapture } from '../kairo-conversation/use-kairo-speech-capture';
import type { useShellStore } from '../../stores/shell';

const HOLD_TO_TALK_MS = 280;

type ShellStore = ReturnType<typeof useShellStore>;
type SpeechCapture = ReturnType<typeof useKairoSpeechCapture>;

export type UseKairoGalaxyOrbVoiceOptions = {
  shell: ShellStore;
  speechCapture: SpeechCapture;
  voiceBlocked: Ref<boolean>;
  orbBusy: Ref<boolean>;
  handsFreeEnabled: Ref<boolean>;
};

export function useKairoGalaxyOrbVoice(options: UseKairoGalaxyOrbVoiceOptions) {
  const kairoSpeaking = ref(false);
  const voiceBeat = ref(false);
  let holdTimer: number | null = null;
  let pointerDownAt = 0;
  let suppressModeToggleClick = false;
  let voiceBeatTimer: number | null = null;
  let unsubscribeSpeaking: (() => void) | null = null;
  let unsubscribeVoiceChunk: (() => void) | null = null;

  function clearHoldTimer(): void {
    if (holdTimer !== null) {
      window.clearTimeout(holdTimer);
      holdTimer = null;
    }
  }

  async function toggleHandsFreeMode(): Promise<void> {
    if (options.voiceBlocked.value) {
      return;
    }
    if (options.handsFreeEnabled.value && options.speechCapture.capturing.value) {
      options.speechCapture.stopCapture();
    }
    await options.shell.saveOperatorPresenceSettingsPatch({
      hands_free_enabled: !options.handsFreeEnabled.value,
    });
  }

  function handleOrbClick(): void {
    if (suppressModeToggleClick) {
      suppressModeToggleClick = false;
      return;
    }
    void toggleHandsFreeMode();
  }

  function handleOrbPttStart(): void {
    if (
      options.voiceBlocked.value ||
      !options.speechCapture.supported ||
      options.orbBusy.value
    ) {
      return;
    }
    options.shell.interruptKairoVoice();
    options.speechCapture.startCapture('manual', { takeover: true });
  }

  function handleOrbPointerDown(event: PointerEvent): void {
    if (
      options.voiceBlocked.value ||
      !options.speechCapture.supported ||
      options.orbBusy.value
    ) {
      return;
    }
    pointerDownAt = Date.now();
    const target = event.currentTarget;
    if (target instanceof HTMLElement && target.setPointerCapture) {
      target.setPointerCapture(event.pointerId);
    }
    if (options.handsFreeEnabled.value) {
      return;
    }
    clearHoldTimer();
    holdTimer = window.setTimeout(() => {
      holdTimer = null;
      if (!options.handsFreeEnabled.value) {
        handleOrbPttStart();
      }
    }, HOLD_TO_TALK_MS);
  }

  function handleOrbPointerUp(event: PointerEvent): void {
    const target = event.currentTarget;
    if (target instanceof HTMLElement && target.releasePointerCapture) {
      try {
        if (target.hasPointerCapture(event.pointerId)) {
          target.releasePointerCapture(event.pointerId);
        }
      } catch {
        // ignore
      }
    }
    clearHoldTimer();
    const heldMs = Date.now() - pointerDownAt;
    const pointerUpResolution = resolveOrbPointerUpIntent({
      captureActive: options.speechCapture.capturing.value,
      handsFreeEnabled: options.handsFreeEnabled.value,
      heldMs,
      holdToTalkMs: HOLD_TO_TALK_MS,
    });
    suppressModeToggleClick = pointerUpResolution.suppressToggleClick;
    if (pointerUpResolution.stopCapture) {
      options.speechCapture.stopCapture();
    }
  }

  onMounted(() => {
    unsubscribeSpeaking = subscribeKairoVoiceSpeaking((active) => {
      kairoSpeaking.value = active;
    });
    unsubscribeVoiceChunk = subscribeKairoVoiceChunk(() => {
      voiceBeat.value = true;
      if (voiceBeatTimer !== null) {
        window.clearTimeout(voiceBeatTimer);
      }
      voiceBeatTimer = window.setTimeout(() => {
        voiceBeat.value = false;
        voiceBeatTimer = null;
      }, 220);
    });
  });

  onBeforeUnmount(() => {
    clearHoldTimer();
    unsubscribeSpeaking?.();
    unsubscribeVoiceChunk?.();
    if (voiceBeatTimer !== null) {
      window.clearTimeout(voiceBeatTimer);
      voiceBeatTimer = null;
    }
  });

  return {
    kairoSpeaking,
    voiceBeat,
    handleOrbClick,
    handleOrbPointerDown,
    handleOrbPointerUp,
  };
}
