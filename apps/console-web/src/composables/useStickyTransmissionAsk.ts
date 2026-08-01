import { computed, ref, watch, type ComputedRef, type Ref } from 'vue';

import {
  isTransmissionAskAnswered,
  markTransmissionAskAnswered,
} from '../lib/vaxon-transmission-reply-state';
import {
  vaxonAffirmReplyCta,
  vaxonLineAsksForReply,
  vaxonLineNeedsIntervention,
} from '../lib/vaxon-reply-prompt';

/**
 * Keep the Needs-you / reply CTA card alive after speech ends.
 * Spoken text often clears or becomes "VAXON is working…" mid-turn.
 */
export function useStickyTransmissionAsk(input: {
  spokenLine: ComputedRef<string>;
  transmissionEmpty: ComputedRef<boolean>;
}): {
  stickyAskLine: Ref<string | null>;
  activeAskLine: ComputedRef<string | null>;
  showReplyActions: ComputedRef<boolean>;
  needsIntervention: ComputedRef<boolean>;
  affirmCta: ComputedRef<string>;
  clearStickyAsk: (line?: string | null) => void;
} {
  const stickyAskLine = ref<string | null>(null);

  watch(
    () => [input.spokenLine.value, input.transmissionEmpty.value] as const,
    ([line, empty]) => {
      const text = String(line ?? '').trim();
      if (!text || empty) {
        return;
      }
      if (!vaxonLineAsksForReply(text) && !vaxonLineNeedsIntervention(text)) {
        return;
      }
      if (isTransmissionAskAnswered(text)) {
        return;
      }
      stickyAskLine.value = text;
    },
  );

  const activeAskLine = computed(() => {
    const live = String(input.spokenLine.value ?? '').trim();
    if (
      live &&
      !input.transmissionEmpty.value &&
      (vaxonLineAsksForReply(live) || vaxonLineNeedsIntervention(live)) &&
      !isTransmissionAskAnswered(live)
    ) {
      return live;
    }
    const sticky = stickyAskLine.value;
    if (sticky && !isTransmissionAskAnswered(sticky)) {
      return sticky;
    }
    return null;
  });

  const showReplyActions = computed(() => Boolean(activeAskLine.value));
  const needsIntervention = computed(() => Boolean(activeAskLine.value));
  const affirmCta = computed(() => vaxonAffirmReplyCta(activeAskLine.value));

  function clearStickyAsk(line?: string | null): void {
    const target = line ?? stickyAskLine.value ?? activeAskLine.value;
    if (target) {
      markTransmissionAskAnswered(target);
    }
    stickyAskLine.value = null;
  }

  return {
    stickyAskLine,
    activeAskLine,
    showReplyActions,
    needsIntervention,
    affirmCta,
    clearStickyAsk,
  };
}
