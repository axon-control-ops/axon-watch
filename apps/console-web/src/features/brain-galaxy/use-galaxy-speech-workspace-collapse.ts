import { watch, type Ref } from 'vue';

import { kairoConversationPhase } from '../kairo-conversation/kairo-conversation-state';
import { galaxySpeechOverlayActive } from './galaxy-speech-overlay-state';

/** Collapse the Workspaces rail while VAXON thinks/speaks or a floating transcript is up. */
export function useGalaxySpeechWorkspaceCollapse(input: {
  kairoSpeechActive: Ref<boolean> | { value: boolean };
  setSpeechCollapseActive: (active: boolean) => void;
}): void {
  watch(
    () =>
      Boolean(input.kairoSpeechActive.value) ||
      galaxySpeechOverlayActive.value ||
      kairoConversationPhase.value === 'thinking' ||
      kairoConversationPhase.value === 'speaking',
    (active) => {
      input.setSpeechCollapseActive(active);
    },
    { immediate: true },
  );
}
