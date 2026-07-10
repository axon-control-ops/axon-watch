import { computed, type ComputedRef, type Ref } from 'vue';

import type { OperatorBriefing, OperatorPresenceSettings } from '../../../contracts/canonical';
import {
  readViewportWidth,
  shouldRequestViewportCompactBriefing,
  shouldUseMobileCompactLayout,
} from '../../../lib/viewport-compact';

interface CreateViewportCompactSliceInput {
  viewportWidth: Ref<number>;
  operatorBriefing: Ref<OperatorBriefing | null>;
  operatorPresenceSettings: Ref<OperatorPresenceSettings>;
  loadOperatorBriefing: (options?: {
    viewportCompact?: boolean;
    background?: boolean;
  }) => Promise<void>;
}

export function createViewportCompactSlice(input: CreateViewportCompactSliceInput) {
  let lastViewportCompactRequested: boolean | null = null;
  let viewportCompactListenerBound = false;

  function getLastViewportCompactRequested(): boolean | null {
    return lastViewportCompactRequested;
  }

  function setLastViewportCompactRequested(value: boolean | null): void {
    lastViewportCompactRequested = value;
  }

  const mobileCompactLayout: ComputedRef<boolean> = computed(() =>
    shouldUseMobileCompactLayout(
      input.viewportWidth.value,
      input.operatorBriefing.value?.operator_presence ?? null,
      input.operatorPresenceSettings.value,
    ),
  );

  function syncViewportCompactFromResize(): void {
    if (typeof window === 'undefined') {
      return;
    }

    input.viewportWidth.value = readViewportWidth(window);
    const shouldRequest = shouldRequestViewportCompactBriefing(
      input.viewportWidth.value,
      input.operatorBriefing.value?.operator_presence ?? null,
      input.operatorPresenceSettings.value,
    );
    if (shouldRequest === lastViewportCompactRequested) {
      return;
    }
    void input.loadOperatorBriefing({ viewportCompact: shouldRequest });
  }

  function bindViewportCompactListener(): void {
    if (typeof window === 'undefined' || viewportCompactListenerBound) {
      return;
    }
    input.viewportWidth.value = readViewportWidth(window);
    window.addEventListener('resize', syncViewportCompactFromResize);
    viewportCompactListenerBound = true;
  }

  function unbindViewportCompactListener(): void {
    if (typeof window === 'undefined' || !viewportCompactListenerBound) {
      return;
    }
    window.removeEventListener('resize', syncViewportCompactFromResize);
    viewportCompactListenerBound = false;
  }

  return {
    mobileCompactLayout,
    getLastViewportCompactRequested,
    setLastViewportCompactRequested,
    syncViewportCompactFromResize,
    bindViewportCompactListener,
    unbindViewportCompactListener,
  };
}
