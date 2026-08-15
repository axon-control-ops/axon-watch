import { computed, ref } from 'vue';

import {
  loadLeadReviewFromPlan,
  type LeadReviewOverlayPayload,
} from '../../lib/load-lead-review';

const open = ref(false);
const loading = ref(false);
const payload = ref<LeadReviewOverlayPayload | null>(null);
const error = ref<string | null>(null);

export const leadReviewOverlayOpen = computed(() => open.value);
export const leadReviewOverlayLoading = computed(() => loading.value);
export const leadReviewOverlayPayload = computed(() => payload.value);
export const leadReviewOverlayError = computed(() => error.value);

export async function openLeadReviewOverlay(planId: string): Promise<boolean> {
  const cleaned = String(planId || '').trim();
  if (!cleaned) {
    return false;
  }

  open.value = true;
  loading.value = true;
  error.value = null;
  payload.value = null;

  try {
    const result = await loadLeadReviewFromPlan(cleaned);
    if (!result.ok) {
      error.value = result.error;
      return false;
    }
    payload.value = result.payload;
    return true;
  } catch (loadError) {
    error.value =
      loadError instanceof Error ? loadError.message : 'Could not load the Lead rollup.';
    return false;
  } finally {
    loading.value = false;
  }
}

export function closeLeadReviewOverlay(): void {
  open.value = false;
  loading.value = false;
  error.value = null;
  payload.value = null;
}

export function resetLeadReviewOverlayStateForTests(): void {
  closeLeadReviewOverlay();
}
