import { computed, onBeforeUnmount, onMounted, ref, type ComputedRef } from 'vue';

import {
  clearVaxonBriefingInteraction,
  getVaxonBriefingInteraction,
  recordVaxonBriefingInteraction,
  vaxonBriefingInteractionKey,
} from '../../lib/vaxon-briefing-interaction';
import {
  getKairoVoiceUtteranceState,
  subscribeKairoVoiceUtterance,
} from '../../lib/kairo-voice-utterance';
import { kairoVoiceFollowupExpiresAt } from '../../lib/kairo-voice-followup-window';

export function useVaxonRosterVoiceDock(
  speechActive: ComputedRef<boolean>,
  workspaceId: ComputedRef<string | null | undefined>,
) {
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
      const text = state.text?.trim();
      if (text) {
        lastLine.value = text;
        const ws = workspaceId.value?.trim();
        if (ws) {
          recordVaxonBriefingInteraction({
            workspaceId: ws,
            line: text,
            utteranceKey: vaxonBriefingInteractionKey(text, state.speaker.id),
          });
        }
      }
    }
  }

  onMounted(() => {
    const ws = workspaceId.value?.trim();
    if (ws) {
      const pending = getVaxonBriefingInteraction(ws);
      if (pending) {
        lastSpeakerWasVaxon.value = true;
        lastLine.value = pending.line;
      }
    }
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
  const pendingInteraction = computed(() => {
    const ws = workspaceId.value?.trim();
    return ws ? getVaxonBriefingInteraction(ws) : null;
  });
  const displayLine = computed(
    () => pendingInteraction.value?.line || lastLine.value,
  );
  const visible = computed(
    () =>
      Boolean(displayLine.value.trim()) &&
      (speaking.value || followupActive.value || Boolean(pendingInteraction.value)),
  );

  function dismiss(): void {
    const ws = workspaceId.value?.trim();
    if (ws) {
      clearVaxonBriefingInteraction(ws);
    }
    lastLine.value = '';
    lastSpeakerWasVaxon.value = false;
  }

  function markReplied(): void {
    const ws = workspaceId.value?.trim();
    if (ws) {
      clearVaxonBriefingInteraction(ws);
    }
  }

  return {
    visible,
    speaking,
    line: displayLine,
    remainingSeconds,
    dismiss,
    markReplied,
  };
}
