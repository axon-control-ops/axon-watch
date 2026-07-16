<script setup lang="ts">
import { computed } from 'vue';
import BriefingSurfaceFollowupPrompt from '../../../features/kairo-conversation/BriefingSurfaceFollowupPrompt.vue';
import AgentDockComposerImageLightbox from './AgentDockComposerImageLightbox.vue';
import AgentDockApprovalBanner from './AgentDockApprovalBanner.vue';
import AgentDockDebugReproduceBanner from './AgentDockDebugReproduceBanner.vue';
import AgentDockFullAccessConsent from './AgentDockFullAccessConsent.vue';
import AgentDockSandboxConsent from './AgentDockSandboxConsent.vue';
import AgentDockIdeVoiceHint from './AgentDockIdeVoiceHint.vue';
import AgentDockPlanSwitchBanner from './AgentDockPlanSwitchBanner.vue';
import type { PlanSoftSwitchNotice } from '../../../composables/agent-dock/use-composer-actions';
import type { DebugReproduceRequest } from '../../../lib/debug-reproduce-view';
import type { ComposerClipboardImage } from '../../../lib/composer-clipboard-paste';
import {
  clearActiveIdeNarrationOverrideHint,
  getActiveIdeNarrationOverrideHint,
} from '../../../lib/ide-narration-override-hint';

const ideVoiceNarrationHint = computed(() => getActiveIdeNarrationOverrideHint());

defineProps<{
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
  planSoftSwitchReasonLabel?: string;
}>();

const emit = defineEmits<{
  'update:fullAccessConsentChecked': [checked: boolean];
  cancelFullAccessConsent: [];
  confirmFullAccessConsent: [];
  'update:sandboxConsentChecked': [checked: boolean];
  cancelSandboxConsent: [];
  confirmSandboxConsent: [];
  closeComposerImageLightbox: [];
  debugReproduceProceed: [messageId: string];
  debugReproduceDismiss: [];
  approveRun: [];
  rejectRun: [];
  undoPlanSoftSwitch: [];
  dismissPlanSoftSwitch: [];
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
    @dismiss="emit('debugReproduceDismiss')"
  />
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
    @undo="emit('undoPlanSoftSwitch')"
    @dismiss="emit('dismissPlanSoftSwitch')"
  />
</template>
