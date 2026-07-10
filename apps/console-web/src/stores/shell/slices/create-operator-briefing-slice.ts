import type { Ref } from 'vue';

import { fetchOperatorBriefing } from '../../../api/control-plane';
import type {
  ApprovalRecord,
  OperatorBriefing,
  OperatorPresenceSettings,
} from '../../../contracts/canonical';
import { shouldRequestViewportCompactBriefing } from '../../../lib/viewport-compact';
import type { BriefingLoadState } from '../types';

interface CreateOperatorBriefingSliceInput {
  operatorBriefing: Ref<OperatorBriefing | null>;
  briefingLoadState: Ref<BriefingLoadState>;
  briefingError: Ref<string | null>;
  approvals: Ref<ApprovalRecord[]>;
  viewportWidth: Ref<number>;
  operatorPresenceSettings: Ref<OperatorPresenceSettings>;
  currentWorkspaceId: () => string | null;
  applyOperatorDockDefaults: () => void;
  getLastViewportCompactRequested: () => boolean | null;
  setLastViewportCompactRequested: (value: boolean | null) => void;
}

export function createOperatorBriefingSlice(input: CreateOperatorBriefingSliceInput) {
  let operatorBriefingFetchInFlight: Promise<void> | null = null;

  async function loadOperatorBriefing(options?: {
    viewportCompact?: boolean;
    background?: boolean;
  }): Promise<void> {
    if (operatorBriefingFetchInFlight) {
      return operatorBriefingFetchInFlight;
    }

    operatorBriefingFetchInFlight = (async () => {
      const backgroundRefresh =
        options?.background === true && input.briefingLoadState.value === 'loaded';
      if (!backgroundRefresh) {
        input.briefingLoadState.value = 'loading';
        input.briefingError.value = null;
      }

      const viewportCompact =
        options?.viewportCompact ??
        shouldRequestViewportCompactBriefing(
          input.viewportWidth.value,
          input.operatorBriefing.value?.operator_presence ?? null,
          input.operatorPresenceSettings.value,
        );

      try {
        input.operatorBriefing.value = await fetchOperatorBriefing({
          viewportCompact,
          workspaceId: input.currentWorkspaceId(),
        });
        input.setLastViewportCompactRequested(viewportCompact);
        input.approvals.value = input.operatorBriefing.value.pending_approvals.items;
        input.briefingLoadState.value = 'loaded';
        input.applyOperatorDockDefaults();
      } catch (error) {
        if (!backgroundRefresh) {
          input.briefingLoadState.value = 'error';
          input.briefingError.value =
            error instanceof Error ? error.message : 'operator briefing request failed';
        }
      }
    })();

    try {
      await operatorBriefingFetchInFlight;
    } finally {
      operatorBriefingFetchInFlight = null;
    }
  }

  return {
    loadOperatorBriefing,
  };
}
