import { computed, onBeforeUnmount, onMounted, ref } from 'vue';

import {
  briefingSurfaceOfferExpiresAt,
  BRIEFING_SURFACE_FOLLOWUP_HINT,
  isBriefingSurfaceOfferActive,
} from './conversation-briefing-surface';

export function useBriefingSurfacePrompt() {
  const now = ref(Date.now());
  let timer: ReturnType<typeof globalThis.setInterval> | null = null;

  onMounted(() => {
    timer = globalThis.setInterval(() => {
      now.value = Date.now();
    }, 1000);
  });

  onBeforeUnmount(() => {
    if (timer !== null) {
      globalThis.clearInterval(timer);
      timer = null;
    }
  });

  const active = computed(() => isBriefingSurfaceOfferActive(now.value));
  const remainingSeconds = computed(() => {
    const expiresAt = briefingSurfaceOfferExpiresAt.value;
    if (!expiresAt) {
      return 0;
    }
    return Math.max(0, Math.ceil((expiresAt - now.value) / 1000));
  });

  return {
    active,
    remainingSeconds,
    hint: BRIEFING_SURFACE_FOLLOWUP_HINT,
  };
}
