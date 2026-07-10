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
  async function loadRuntimeStatus(forceRefresh = false): Promise<void> {
    input.runtimeStatusLoadState.value = 'loading';
    input.runtimeStatusError.value = null;

    try {
      const status = await fetchRuntimeStatus({ forceRefresh });
      input.runtimeStatus.value = status;
      input.runtimeStatusLoadState.value = 'loaded';
    } catch (error) {
      input.runtimeStatusLoadState.value = 'error';
      input.runtimeStatusError.value =
        error instanceof Error ? error.message : 'runtime status request failed';
    }
  }

  async function loadRuntimeMcpTools(): Promise<void> {
    input.runtimeMcpToolsLoadState.value = 'loading';

    try {
      input.runtimeMcpTools.value = await fetchRuntimeMcpTools();
      input.runtimeMcpToolsLoadState.value = 'loaded';
    } catch {
      input.runtimeMcpTools.value = null;
      input.runtimeMcpToolsLoadState.value = 'error';
    }
  }

  return {
    loadRuntimeMcpTools,
    loadRuntimeStatus,
  };
}
