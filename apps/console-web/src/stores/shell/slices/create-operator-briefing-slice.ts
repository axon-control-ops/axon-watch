import type { Ref } from 'vue';

import { fetchOperatorBriefing } from '../../../api/control-plane';
import type {
  ApprovalRecord,
  OperatorBriefing,
  OperatorPresenceSettings,
} from '../../../contracts/canonical';
import { submitKairoConversationTranscript } from '../../../features/kairo-conversation/kairo-conversation-bus';
import {
  markReportTheaterAutoStarted,
  shouldAutoStartReportTheater,
  shouldStartReportTheaterForBriefing,
} from '../../../features/report-theater/report-theater-auto-start';
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
  const observedFullBriefKeyByWorkspace = new Map<string, string>();

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
        // #region agent log
        fetch('http://127.0.0.1:7706/ingest/90bcaec2-2b39-4d4a-84b5-157c12735440',{method:'POST',headers:{'Content-Type':'application/json','X-Debug-Session-Id':'bef50e'},body:JSON.stringify({sessionId:'bef50e',runId:'post-fix',hypothesisId:'H2,H3,H4',location:'create-operator-briefing-slice.ts:fetch',message:'browser received operator briefing',data:{workspaceKey:requestedWorkspaceKey,light,background:options?.background===true,presenceState:briefing.operator_presence?.presence_state??null,alertEligible:briefing.operator_presence?.spoken_alert?.eligible??false,alertReason:briefing.operator_presence?.spoken_alert?.reason??null,autonomyMode:briefing.operator_presence?.settings?.autonomy_mode??null,readinessScore:briefing.production_readiness?.score??null,readinessGrade:briefing.production_readiness?.grade??null,proactiveDuplex:briefing.operator_presence?.settings?.proactive_duplex_enabled??null,handsFree:briefing.operator_presence?.settings?.hands_free_enabled??null},timestamp:Date.now()})}).catch(()=>{});
        // #endregion
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
            production_readiness: briefing.production_readiness,
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

        if (!light) {
          const settings =
            briefing.operator_presence?.settings ?? input.operatorPresenceSettings.value;
          const briefKey = [
            briefing.advise ?? '',
            briefing.notice ?? '',
            String(briefing.awaiting_engagement_count ?? 0),
            briefing.top_signals?.[0]?.signal_id ?? '',
            String(briefing.pending_approvals?.count ?? 0),
          ].join('|');
          const previousBriefKey = observedFullBriefKeyByWorkspace.get(requestedWorkspaceKey);
          observedFullBriefKeyByWorkspace.set(requestedWorkspaceKey, briefKey);
          const autoStartEligible = shouldAutoStartReportTheater({
            autonomyMode: settings.autonomy_mode,
            privacyMode: Boolean(settings.privacy_mode),
            spokenAlertsEnabled: settings.spoken_alerts_enabled !== false,
            pendingApprovals: briefing.pending_approvals?.count ?? 0,
            topSignalCount: briefing.top_signals?.length ?? 0,
            awaitingEngagementCount: briefing.awaiting_engagement_count ?? 0,
            degradedActive: Boolean(briefing.degraded?.active),
            briefKey,
          });
          const shouldStart = shouldStartReportTheaterForBriefing({
            autonomyMode: settings.autonomy_mode,
            previousBriefKey,
            currentBriefKey: briefKey,
            eligible: autoStartEligible,
          });
          if (shouldStart) {
            markReportTheaterAutoStarted(briefKey);
            void submitKairoConversationTranscript('REPORT');
          }
        }
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

  async function refreshOperatorPresence(): Promise<void> {
    await loadOperatorBriefing({ background: true, light: true });
  }

  return {
    loadOperatorBriefing,
    refreshOperatorPresence,
  };
}
