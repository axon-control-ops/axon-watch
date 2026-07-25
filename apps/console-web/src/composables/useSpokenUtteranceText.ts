/** Reactive text currently being spoken — keeps speaker chips / left-rail voice in sync. */

import { onBeforeUnmount, onMounted, ref } from 'vue';

import {
  getKairoVoiceUtteranceState,
  subscribeKairoVoiceUtterance,
  type KairoVoiceSpeaker,
} from '../lib/kairo-voice-utterance';
import { stripAgentStreamFenceMarkers } from '../lib/agent-live-line-view';

export function useSpokenUtteranceText() {
  const initial = getKairoVoiceUtteranceState();
  const spokenText = ref<string | null>(
    initial.text?.trim() ? stripAgentStreamFenceMarkers(initial.text) : null,
  );
  const speaker = ref<KairoVoiceSpeaker | null>(initial.speaker);

  let unsubscribe: (() => void) | null = null;

  onMounted(() => {
    unsubscribe = subscribeKairoVoiceUtterance((state) => {
      const next = state.text?.trim() ? stripAgentStreamFenceMarkers(state.text) : null;
      spokenText.value = next || null;
      speaker.value = next ? state.speaker : null;
    });
  });

  onBeforeUnmount(() => {
    unsubscribe?.();
    unsubscribe = null;
  });

  return { spokenText, speaker };
}
