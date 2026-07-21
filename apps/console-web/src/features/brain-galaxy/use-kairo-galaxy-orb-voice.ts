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
  /** Short tap handler — when set, replaces the default hands-free toggle on tap. */
  onShortTap?: () => void;
};

export function useKairoGalaxyOrbVoice(options: UseKairoGalaxyOrbVoiceOptions) {
  const kairoSpeaking = ref(false);
  const voiceBeat = ref(false);
  /** Brief visual pulse when hands-free / manual mode flips. */
  const modeFlash = ref(false);
  let holdTimer: number | null = null;
  let pointerDownAt = 0;
  let ignoreSynthesizedClick = false;
  let modeFlashTimer: number | null = null;
  let voiceBeatTimer: number | null = null;
  let unsubscribeSpeaking: (() => void) | null = null;
  let unsubscribeVoiceChunk: (() => void) | null = null;
  let toggleInFlight = false;

  function clearHoldTimer(): void {
    if (holdTimer !== null) {
      window.clearTimeout(holdTimer);
      holdTimer = null;
    }
  }

  function flashModeChange(): void {
    modeFlash.value = true;
    if (modeFlashTimer !== null) {
      window.clearTimeout(modeFlashTimer);
    }
    modeFlashTimer = window.setTimeout(() => {
      modeFlash.value = false;
      modeFlashTimer = null;
    }, 700);
  }

  async function toggleHandsFreeMode(source: string): Promise<void> {
    if (options.voiceBlocked.value || toggleInFlight) {
      return;
    }
    toggleInFlight = true;
    const enabling = !options.handsFreeEnabled.value;
    // Flash immediately — store patch is optimistic; do not hold the lock through
    // network + briefing reload or rapid taps look dead.
    flashModeChange();
    if (options.handsFreeEnabled.value && options.speechCapture.capturing.value) {
      options.speechCapture.stopCapture();
    }
    void options.shell
      .saveOperatorPresenceSettingsPatch(
        enabling
          ? { hands_free_enabled: true, stt_mode: 'cloud' }
          : { hands_free_enabled: false, proactive_duplex_enabled: false },
      )
      .catch(() => undefined);
    window.setTimeout(() => {
      toggleInFlight = false;
    }, 320);
  }

  function runShortTap(source: string): void {
    if (options.onShortTap) {
      options.onShortTap();
      return;
    }
    void toggleHandsFreeMode(source);
  }

  /** @deprecated Prefer pointer-up short-tap path; kept for keyboard activation. */
  function handleOrbClick(): void {
    if (ignoreSynthesizedClick) {
      ignoreSynthesizedClick = false;
      return;
    }
    runShortTap('click');
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
    // Swallow the synthetic click that follows pointerup so we never double-toggle
    // (pointerup + click would flip mode twice and look like "nothing happened").
    ignoreSynthesizedClick = true;
    window.setTimeout(() => {
      ignoreSynthesizedClick = false;
    }, 450);

    if (pointerUpResolution.stopCapture) {
      options.speechCapture.stopCapture();
    }

    // Short tap toggles mode here — do not rely on the click event.
    if (!pointerUpResolution.suppressToggleClick && heldMs > 0 && heldMs < HOLD_TO_TALK_MS) {
      runShortTap('pointerup');
    }
  }

  function cancelOrbPointerGesture(): void {
    clearHoldTimer();
    ignoreSynthesizedClick = true;
    window.setTimeout(() => {
      ignoreSynthesizedClick = false;
    }, 450);
    if (options.speechCapture.capturing.value) {
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
    if (modeFlashTimer !== null) {
      window.clearTimeout(modeFlashTimer);
      modeFlashTimer = null;
    }
  });

  return {
    kairoSpeaking,
    voiceBeat,
    modeFlash,
    handleOrbClick,
    handleOrbPointerDown,
    handleOrbPointerUp,
    cancelOrbPointerGesture,
    toggleHandsFreeMode,
  };
}
