/** Reactive text currently being spoken — keeps RUN TRANSCRIPT / speaker chips in sync. */

import { onBeforeUnmount, onMounted, ref } from 'vue';

import {
  getKairoVoiceUtterance,
  subscribeKairoVoiceUtterance,
} from '../lib/kairo-voice-utterance';
import { stripAgentStreamFenceMarkers } from '../lib/agent-live-line-view';

export function useSpokenUtteranceText() {
  const spokenText = ref<string | null>(getKairoVoiceUtterance());

  let unsubscribe: (() => void) | null = null;

  onMounted(() => {
    unsubscribe = subscribeKairoVoiceUtterance((state) => {
      const next = state.text?.trim() ? stripAgentStreamFenceMarkers(state.text) : null;
      spokenText.value = next || null;
    });
  });

  onBeforeUnmount(() => {
    unsubscribe?.();
    unsubscribe = null;
  });

  return { spokenText };
}
