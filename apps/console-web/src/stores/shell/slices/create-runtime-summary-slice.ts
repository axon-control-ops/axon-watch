import type { Ref } from 'vue';

import { fetchRuntimeSummary } from '../../../api/control-plane';
import type { RuntimeSummary } from '../../../contracts/canonical';
import type { RuntimeSummaryLoadState } from '../types';

interface CreateRuntimeSummarySliceInput {
  runtimeSummary: Ref<RuntimeSummary | null>;
  runtimeSummaryLoadState: Ref<RuntimeSummaryLoadState>;
  runtimeSummaryError: Ref<string | null>;
}

export function createRuntimeSummarySlice(input: CreateRuntimeSummarySliceInput) {
  async function loadRuntimeSummary(options?: { background?: boolean }): Promise<void> {
    const background =
      options?.background === true && input.runtimeSummaryLoadState.value === 'loaded';
    if (!background) {
      input.runtimeSummaryLoadState.value = 'loading';
      input.runtimeSummaryError.value = null;
    }

    try {
      const summary = await fetchRuntimeSummary();
      input.runtimeSummary.value = summary;
      input.runtimeSummaryLoadState.value = 'loaded';
    } catch (error) {
      if (!background) {
        input.runtimeSummaryLoadState.value = 'error';
        input.runtimeSummaryError.value =
          error instanceof Error ? error.message : 'runtime summary request failed';
      }
    }
  }

  return {
    loadRuntimeSummary,
  };
}
