import { computed, ref, watch, type ComputedRef, type Ref } from 'vue';

import {
  isTransmissionAskAnswered,
  markTransmissionAskAnswered,
  transmissionAskFingerprint,
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
      // #region agent log
      fetch('http://127.0.0.1:7706/ingest/90bcaec2-2b39-4d4a-84b5-157c12735440', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Debug-Session-Id': 'db8bb4',
        },
        body: JSON.stringify({
          sessionId: 'db8bb4',
          runId: 'sticky-ask',
          hypothesisId: 'Y1',
          location: 'useStickyTransmissionAsk.ts:pin',
          message: 'Pinned sticky Needs-you ask',
          data: {
            preview: text.slice(0, 72),
            fingerprint: transmissionAskFingerprint(text).slice(0, 48),
          },
          timestamp: Date.now(),
        }),
      }).catch(() => {});
      // #endregion
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
