import type { Ref } from 'vue';

import {
  fetchOperatorBrainGraph,
  fetchOperatorFleetHealth,
  type FleetHealthSnapshot,
} from '../../../api/control-plane';
import { normalizeBrainGraphSnapshot } from '../../../lib/kairo-entity-labels';
import type { BrainGraphSnapshot } from '../../../lib/operator-brain-graph-view';

type ProbeLoadState = 'idle' | 'loading' | 'loaded' | 'error';

interface CreateOperatorProbesSliceInput {
  operatorFleetHealth: Ref<FleetHealthSnapshot | null>;
  operatorFleetHealthLoadState: Ref<ProbeLoadState>;
  operatorFleetHealthError: Ref<string | null>;
  operatorBrainGraph: Ref<BrainGraphSnapshot | null>;
  operatorBrainGraphLoadState: Ref<ProbeLoadState>;
  operatorBrainGraphError: Ref<string | null>;
}

export function createOperatorProbesSlice(input: CreateOperatorProbesSliceInput) {
  async function loadOperatorFleetHealth(options?: { background?: boolean }): Promise<void> {
    const backgroundRefresh =
      options?.background === true && input.operatorFleetHealthLoadState.value === 'loaded';
    if (!backgroundRefresh) {
      input.operatorFleetHealthLoadState.value = 'loading';
      input.operatorFleetHealthError.value = null;
    }

    try {
      input.operatorFleetHealth.value = await fetchOperatorFleetHealth();
      input.operatorFleetHealthLoadState.value = 'loaded';
    } catch (error) {
      if (!backgroundRefresh) {
        input.operatorFleetHealthLoadState.value = 'error';
        input.operatorFleetHealthError.value =
          error instanceof Error ? error.message : 'operator fleet health request failed';
      }
    }
  }

  async function loadOperatorBrainGraph(options?: { background?: boolean }): Promise<void> {
    const backgroundRefresh =
      options?.background === true && input.operatorBrainGraphLoadState.value === 'loaded';
    if (!backgroundRefresh) {
      input.operatorBrainGraphLoadState.value = 'loading';
      input.operatorBrainGraphError.value = null;
    }

    try {
      input.operatorBrainGraph.value = normalizeBrainGraphSnapshot(await fetchOperatorBrainGraph());
      input.operatorBrainGraphLoadState.value = 'loaded';
    } catch (error) {
      if (!backgroundRefresh) {
        input.operatorBrainGraphLoadState.value = 'error';
        input.operatorBrainGraphError.value =
          error instanceof Error ? error.message : 'operator brain graph request failed';
      }
    }
  }

  return {
    loadOperatorBrainGraph,
    loadOperatorFleetHealth,
  };
}
