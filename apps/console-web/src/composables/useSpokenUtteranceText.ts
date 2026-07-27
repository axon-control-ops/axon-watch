/** Reactive text currently being spoken — keeps speaker chips / left-rail voice in sync. */

import { onBeforeUnmount, onMounted, ref } from 'vue';

import {
  getKairoVoiceUtteranceState,
  subscribeKairoVoiceUtterance,
  type KairoVoiceSpeaker,
} from '../lib/kairo-voice-utterance';
import { sanitizeAgentThinkingForOperator, stripAgentStreamFenceMarkers } from '../lib/agent-live-line-view';

function operatorFacingSpokenText(text: string | null | undefined): string | null {
  const raw = text?.trim();
  if (!raw) {
    return null;
  }
  return (
    sanitizeAgentThinkingForOperator(raw) ||
    stripAgentStreamFenceMarkers(raw) ||
    null
  );
}

export function useSpokenUtteranceText() {
  const initial = getKairoVoiceUtteranceState();
  const spokenText = ref<string | null>(operatorFacingSpokenText(initial.text));
  const speaker = ref<KairoVoiceSpeaker | null>(initial.speaker);

  let unsubscribe: (() => void) | null = null;

  onMounted(() => {
    unsubscribe = subscribeKairoVoiceUtterance((state) => {
      const next = operatorFacingSpokenText(state.text);
      spokenText.value = next;
      speaker.value = next ? state.speaker : null;
    });
  });

  onBeforeUnmount(() => {
    unsubscribe?.();
    unsubscribe = null;
  });

  return { spokenText, speaker };
}
