<script setup lang="ts">
import { computed } from 'vue';
import AgentDockComposerImageLightbox from './AgentDockComposerImageLightbox.vue';
import AgentDockApprovalBanner from './AgentDockApprovalBanner.vue';
import AgentDockDebugReproduceBanner from './AgentDockDebugReproduceBanner.vue';
import AgentDockFullAccessConsent from './AgentDockFullAccessConsent.vue';
import AgentDockSandboxConsent from './AgentDockSandboxConsent.vue';
import AgentDockIdeVoiceHint from './AgentDockIdeVoiceHint.vue';
import AgentDockPlanSwitchBanner from './AgentDockPlanSwitchBanner.vue';
import AgentDockTeammateRouteBanner from './AgentDockTeammateRouteBanner.vue';
import AgentDockWorkspaceScopeBanner from './AgentDockWorkspaceScopeBanner.vue';
import type {
  PlanSoftSwitchNotice,
  WorkspaceScopeNotice,
} from '../../../composables/agent-dock/use-composer-actions';
import type { TeammateRouteNotice } from '../../../lib/teammate-route-notice';
import { PLAN_SOFT_SWITCH_REASON_LABEL } from '../../../composables/agent-dock/use-agent-dock-composer-toolbar-props';
import type { DebugReproduceRequest } from '../../../lib/debug-reproduce-view';
import type { ComposerClipboardImage } from '../../../lib/composer-clipboard-paste';
import {
  clearActiveIdeNarrationOverrideHint,
  getActiveIdeNarrationOverrideHint,
} from '../../../lib/ide-narration-override-hint';

const ideVoiceNarrationHint = computed(() => getActiveIdeNarrationOverrideHint());

const props = defineProps<{
  showFullAccessConsent: boolean;
  fullAccessConsentChecked: boolean;
  showSandboxConsent: boolean;
  sandboxConsentChecked: boolean;
  sandboxSessionPending: boolean;
  sandboxSessionError?: string | null;
  enlargedComposerImage: ComposerClipboardImage | null;
  showDebugReproduceBanner: boolean;
  debugReproduceRequest: DebugReproduceRequest | null;
  commandMutationPending: boolean;
  agentStreamActive: boolean;
  showApprovalBanner: boolean;
  canApproveIdeAgentRun: boolean;
  runMutationPending: boolean;
  planSoftSwitchNotice: PlanSoftSwitchNotice | null;
  teammateRouteNotice: TeammateRouteNotice | null;
  workspaceScopeNotice: WorkspaceScopeNotice | null;
}>();

const planSoftSwitchReasonLabel = computed(() => {
  const notice = props.planSoftSwitchNotice;
  return notice ? PLAN_SOFT_SWITCH_REASON_LABEL[notice.reason] ?? notice.reason : undefined;
});

const planSoftSwitchKind = computed(() => props.planSoftSwitchNotice?.kind ?? 'switched');

const emit = defineEmits<{
  'update:fullAccessConsentChecked': [checked: boolean];
  cancelFullAccessConsent: [];
  confirmFullAccessConsent: [];
  'update:sandboxConsentChecked': [checked: boolean];
  cancelSandboxConsent: [];
  confirmSandboxConsent: [];
  closeComposerImageLightbox: [];
  debugReproduceProceed: [messageId: string];
  debugReproduceResolved: [messageId: string];
  approveRun: [];
  rejectRun: [];
  undoPlanSoftSwitch: [];
  dismissPlanSoftSwitch: [];
  acceptPlanSoftSwitchOffer: [];
  declinePlanSoftSwitchOffer: [];
  undoTeammateRoute: [];
  dismissTeammateRoute: [];
  switchWorkspaceScope: [];
  dismissWorkspaceScope: [stayHere?: boolean];
}>();
</script>

<template>
  <AgentDockFullAccessConsent
    :show="showFullAccessConsent"
    :checked="fullAccessConsentChecked"
    @update:checked="emit('update:fullAccessConsentChecked', $event)"
    @cancel="emit('cancelFullAccessConsent')"
    @confirm="emit('confirmFullAccessConsent')"
  />
  <AgentDockSandboxConsent
    :show="showSandboxConsent"
    :checked="sandboxConsentChecked"
    :pending="sandboxSessionPending"
    :error="sandboxSessionError ?? undefined"
    @update:checked="emit('update:sandboxConsentChecked', $event)"
    @cancel="emit('cancelSandboxConsent')"
    @confirm="emit('confirmSandboxConsent')"
  />
  <AgentDockComposerImageLightbox
    :image="enlargedComposerImage"
    @close="emit('closeComposerImageLightbox')"
  />
  <AgentDockDebugReproduceBanner
    v-if="showDebugReproduceBanner && debugReproduceRequest"
    :request="debugReproduceRequest"
    :pending="commandMutationPending || agentStreamActive"
    @proceed="emit('debugReproduceProceed', debugReproduceRequest.messageId)"
    @resolve="emit('debugReproduceResolved', debugReproduceRequest.messageId)"
  />
  <!-- Soft Attention actions live on IdeAgentReviewStrip; no copy-only banner under it. -->
  <AgentDockApprovalBanner
    :show="showApprovalBanner"
    :can-approve="canApproveIdeAgentRun"
    :reject-pending="runMutationPending"
    @approve="emit('approveRun')"
    @reject="emit('rejectRun')"
  />
  <AgentDockIdeVoiceHint
    v-if="ideVoiceNarrationHint"
    :message="ideVoiceNarrationHint"
    @dismiss="clearActiveIdeNarrationOverrideHint()"
  />
  <AgentDockPlanSwitchBanner
    :show="Boolean(planSoftSwitchNotice)"
    :reason-label="planSoftSwitchReasonLabel"
    :kind="planSoftSwitchKind"
    @undo="emit('undoPlanSoftSwitch')"
    @dismiss="emit('dismissPlanSoftSwitch')"
    @accept-offer="emit('acceptPlanSoftSwitchOffer')"
    @decline-offer="emit('declinePlanSoftSwitchOffer')"
  />
  <AgentDockTeammateRouteBanner
    :show="Boolean(teammateRouteNotice)"
    :to-name="teammateRouteNotice?.toName ?? ''"
    :role-label="teammateRouteNotice?.toRoleLabel"
    :from-name="teammateRouteNotice?.fromName"
    @undo="emit('undoTeammateRoute')"
    @dismiss="emit('dismissTeammateRoute')"
  />
  <AgentDockWorkspaceScopeBanner
    :show="Boolean(workspaceScopeNotice)"
    :inferred-label="workspaceScopeNotice?.inferredLabel ?? ''"
    :current-label="workspaceScopeNotice?.currentLabel ?? ''"
    @switch-workspace="emit('switchWorkspaceScope')"
    @dismiss="emit('dismissWorkspaceScope', $event)"
  />
</template>
