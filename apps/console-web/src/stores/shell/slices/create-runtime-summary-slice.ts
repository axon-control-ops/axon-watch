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
      // #region agent log
      void import('../../../lib/axon-debug-session-log').then(({ axonDebugSessionLog }) => {
        const runs = summary.active_runs ?? [];
        axonDebugSessionLog({
          hypothesisId: 'H1',
          location: 'create-runtime-summary-slice.ts:loadRuntimeSummary',
          message: 'frontend loaded runtime summary',
          data: {
            activeRunCount: runs.length,
            runIds: runs.map((run) => run.run_id).slice(0, 8),
            watchConnected: summary.watch?.connected ?? null,
            connectorsUnavailable: summary.connectors?.unavailable ?? null,
            degraded: summary.degraded?.active ?? null,
            background,
          },
        });
      });
      // #endregion
    } catch (error) {
      if (!background) {
        input.runtimeSummaryLoadState.value = 'error';
        input.runtimeSummaryError.value =
          error instanceof Error ? error.message : 'runtime summary request failed';
      }
      // #region agent log
      void import('../../../lib/axon-debug-session-log').then(({ axonDebugSessionLog }) => {
        axonDebugSessionLog({
          hypothesisId: 'H1',
          location: 'create-runtime-summary-slice.ts:loadRuntimeSummary',
          message: 'frontend runtime summary failed',
          data: {
            error: error instanceof Error ? error.message : String(error),
            background,
          },
        });
      });
      // #endregion
    }
  }

  return {
    loadRuntimeSummary,
  };
}
