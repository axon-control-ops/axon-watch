import type { Ref } from 'vue';

import {
  fetchRuntimeMcpTools,
  fetchRuntimeStatus,
  type RuntimeMcpToolsSnapshot,
  type RuntimeStatusSnapshot,
} from '../../../api/control-plane';
import type { RuntimeStatusLoadState } from '../types';

interface CreateRuntimeProbesSliceInput {
  runtimeStatus: Ref<RuntimeStatusSnapshot | null>;
  runtimeStatusLoadState: Ref<RuntimeStatusLoadState>;
  runtimeStatusError: Ref<string | null>;
  runtimeMcpTools: Ref<RuntimeMcpToolsSnapshot | null>;
  runtimeMcpToolsLoadState: Ref<RuntimeStatusLoadState>;
}

export function createRuntimeProbesSlice(input: CreateRuntimeProbesSliceInput) {
  let inflightStatus: Promise<void> | null = null;

  async function loadRuntimeStatus(forceRefresh = false): Promise<void> {
    const hasCached = Boolean(input.runtimeStatus.value);

    if (inflightStatus) {
      return inflightStatus;
    }

    if (!hasCached) {
      input.runtimeStatusLoadState.value = 'loading';
      input.runtimeStatusError.value = null;
    }

    inflightStatus = (async () => {
      try {
        const status = await fetchRuntimeStatus({ forceRefresh });
        input.runtimeStatus.value = status;
        input.runtimeStatusLoadState.value = 'loaded';
        input.runtimeStatusError.value = null;
      } catch (error) {
        if (!hasCached) {
          input.runtimeStatusLoadState.value = 'error';
          input.runtimeStatusError.value =
            error instanceof Error ? error.message : 'runtime status request failed';
        }
      } finally {
        inflightStatus = null;
      }
    })();

    return inflightStatus;
  }

  async function loadRuntimeMcpTools(): Promise<void> {
    const hasCached = Boolean(input.runtimeMcpTools.value);
    if (!hasCached) {
      input.runtimeMcpToolsLoadState.value = 'loading';
    }

    try {
      input.runtimeMcpTools.value = await fetchRuntimeMcpTools();
      input.runtimeMcpToolsLoadState.value = 'loaded';
    } catch {
      if (!hasCached) {
        input.runtimeMcpTools.value = null;
        input.runtimeMcpToolsLoadState.value = 'error';
      }
    }
  }

  return {
    loadRuntimeMcpTools,
    loadRuntimeStatus,
  };
}
