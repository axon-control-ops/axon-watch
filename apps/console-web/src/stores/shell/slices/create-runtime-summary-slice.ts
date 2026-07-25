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
  let inflightSummary: Promise<void> | null = null;

  async function loadRuntimeSummary(options?: { background?: boolean }): Promise<void> {
    const hasCached = Boolean(input.runtimeSummary.value);
    const background = options?.background === true || hasCached;

    if (inflightSummary) {
      return inflightSummary;
    }

    if (!background) {
      input.runtimeSummaryLoadState.value = 'loading';
      input.runtimeSummaryError.value = null;
    }

    inflightSummary = (async () => {
      try {
        const summary = await fetchRuntimeSummary();
        input.runtimeSummary.value = summary;
        input.runtimeSummaryLoadState.value = 'loaded';
        input.runtimeSummaryError.value = null;
      } catch (error) {
        if (!hasCached) {
          input.runtimeSummaryLoadState.value = 'error';
          input.runtimeSummaryError.value =
            error instanceof Error ? error.message : 'runtime summary request failed';
        }
      } finally {
        inflightSummary = null;
      }
    })();

    return inflightSummary;
  }

  return {
    loadRuntimeSummary,
  };
}
