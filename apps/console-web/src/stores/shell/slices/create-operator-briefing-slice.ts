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
  let operatorBriefingFetchWorkspaceKey: string | null = null;

  async function loadOperatorBriefing(options?: {
    viewportCompact?: boolean;
    background?: boolean;
    light?: boolean;
  }): Promise<void> {
    const requestedWorkspaceKey = input.currentWorkspaceId()?.trim() || '';
    const light = options?.light === true;

    if (operatorBriefingFetchInFlight) {
      // Light presence ticks must not wait on a cold full briefing rebuild.
      if (light) {
        return;
      }
      if (operatorBriefingFetchWorkspaceKey === requestedWorkspaceKey) {
        return operatorBriefingFetchInFlight;
      }
      await operatorBriefingFetchInFlight;
      if (
        operatorBriefingFetchInFlight &&
        operatorBriefingFetchWorkspaceKey === requestedWorkspaceKey
      ) {
        return operatorBriefingFetchInFlight;
      }
    }

    operatorBriefingFetchWorkspaceKey = requestedWorkspaceKey;
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
        const briefing = await fetchOperatorBriefing({
          viewportCompact,
          workspaceId: input.currentWorkspaceId(),
          light,
        });
        // Drop stale responses if the operator switched workspaces mid-flight.
        if ((input.currentWorkspaceId()?.trim() || '') !== requestedWorkspaceKey) {
          return;
        }
        // Do not let a light presence payload wipe full briefing signals.
        if (light && input.operatorBriefing.value && (briefing.top_signals?.length ?? 0) === 0) {
          input.operatorBriefing.value = {
            ...input.operatorBriefing.value,
            notice: briefing.notice,
            advise: briefing.advise,
            executive_rhythm: briefing.executive_rhythm,
            operator_presence: briefing.operator_presence,
            degraded: briefing.degraded,
            cli_runtime: briefing.cli_runtime,
            connectivity: briefing.connectivity,
            active_runs: briefing.active_runs,
            pending_approvals: briefing.pending_approvals,
            next_safe_actions: briefing.next_safe_actions,
          };
        } else {
          input.operatorBriefing.value = briefing;
          input.approvals.value = briefing.pending_approvals.items;
        }
        input.setLastViewportCompactRequested(viewportCompact);
        input.briefingLoadState.value = 'loaded';
        input.applyOperatorDockDefaults();
      } catch (error) {
        if ((input.currentWorkspaceId()?.trim() || '') !== requestedWorkspaceKey) {
          return;
        }
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
      if (operatorBriefingFetchWorkspaceKey === requestedWorkspaceKey) {
        operatorBriefingFetchInFlight = null;
        operatorBriefingFetchWorkspaceKey = null;
      }
    }
  }

  return {
    loadOperatorBriefing,
  };
}
