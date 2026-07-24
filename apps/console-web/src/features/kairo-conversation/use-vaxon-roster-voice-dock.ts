import { computed, onBeforeUnmount, onMounted, ref, type ComputedRef } from 'vue';

import {
  getKairoVoiceUtteranceState,
  subscribeKairoVoiceUtterance,
} from '../../lib/kairo-voice-utterance';
import { kairoVoiceFollowupExpiresAt } from '../../lib/kairo-voice-followup-window';

export function useVaxonRosterVoiceDock(speechActive: ComputedRef<boolean>) {
  const now = ref(Date.now());
  const lastLine = ref('');
  const lastSpeakerWasVaxon = ref(false);
  let timer: ReturnType<typeof globalThis.setInterval> | null = null;
  let unsubscribe: (() => void) | null = null;

  function applyUtterance(): void {
    const state = getKairoVoiceUtteranceState();
    if (state.speaker?.kind === 'employee') {
      lastSpeakerWasVaxon.value = false;
      return;
    }
    if (state.speaker?.kind === 'vaxon') {
      lastSpeakerWasVaxon.value = true;
      if (state.text?.trim()) {
        lastLine.value = state.text.trim();
      }
    }
  }

  onMounted(() => {
    applyUtterance();
    unsubscribe = subscribeKairoVoiceUtterance(() => applyUtterance());
    timer = globalThis.setInterval(() => {
      now.value = Date.now();
    }, 1000);
  });

  onBeforeUnmount(() => {
    unsubscribe?.();
    unsubscribe = null;
    if (timer !== null) {
      globalThis.clearInterval(timer);
      timer = null;
    }
  });

  const remainingSeconds = computed(() => {
    const expiresAt = kairoVoiceFollowupExpiresAt.value;
    if (!expiresAt) {
      return 0;
    }
    return Math.max(0, Math.ceil((expiresAt - now.value) / 1000));
  });
  const followupActive = computed(() => remainingSeconds.value > 0);
  const speaking = computed(() => lastSpeakerWasVaxon.value && speechActive.value);
  const visible = computed(
    () => lastSpeakerWasVaxon.value && (speaking.value || followupActive.value),
  );

  return {
    visible,
    speaking,
    line: computed(() => lastLine.value),
    remainingSeconds,
  };
}
