<script setup lang="ts">
import BriefingSurfaceFollowupPrompt from '../../features/kairo-conversation/BriefingSurfaceFollowupPrompt.vue';
import { useAgentDockComposer } from '../../composables/useAgentDockComposer';
import { useAgentDockComposerToolbarProps } from '../../composables/agent-dock/use-agent-dock-composer-toolbar-props';
import AgentDockComposerAccessBanner from './agent-dock/AgentDockComposerAccessBanner.vue';
import AgentDockComposerChrome from './agent-dock/AgentDockComposerChrome.vue';
import AgentDockComposerInput from './agent-dock/AgentDockComposerInput.vue';
import AgentDockComposerToolbar from './agent-dock/AgentDockComposerToolbar.vue';
import AgentDockKairoComposerFooter from './agent-dock/AgentDockKairoComposerFooter.vue';

const composer = useAgentDockComposer();
const toolbarProps = useAgentDockComposerToolbarProps(composer);
</script>

<template>
  <AgentDockComposerChrome
    :show-full-access-consent="composer.showFullAccessConsent.value"
    :full-access-consent-checked="composer.fullAccessConsentChecked.value"
    :show-sandbox-consent="composer.showSandboxConsent.value"
    :sandbox-consent-checked="composer.sandboxConsentChecked.value"
    :sandbox-session-pending="composer.sandboxSessionPending.value"
    :sandbox-session-error="composer.sandboxSessionError.value"
    :enlarged-composer-image="composer.enlargedComposerImage.value"
    :show-debug-reproduce-banner="composer.showDebugReproduceBanner.value"
    :debug-reproduce-request="composer.debugReproduceRequest.value"
    :command-mutation-pending="composer.shell.commandMutationState === 'submitting'"
    :agent-stream-active="composer.shell.agentStreamActive"
    :show-approval-banner="composer.showApprovalBanner.value"
    :can-approve-ide-agent-run="composer.shell.canApproveIdeAgentRun"
    :run-mutation-pending="composer.shell.runMutationPending"
    :plan-soft-switch-notice="composer.planSoftSwitchNotice.value"
    :teammate-route-notice="composer.teammateRouteNotice.value"
    @update:full-access-consent-checked="composer.fullAccessConsentChecked.value = $event"
    @cancel-full-access-consent="composer.cancelFullAccessConsent()"
    @confirm-full-access-consent="composer.confirmFullAccessConsent()"
    @update:sandbox-consent-checked="composer.sandboxConsentChecked.value = $event"
    @cancel-sandbox-consent="composer.cancelSandboxConsent()"
    @confirm-sandbox-consent="composer.confirmSandboxConsent()"
    @close-composer-image-lightbox="composer.closeComposerImageLightbox()"
    @debug-reproduce-proceed="composer.handleDebugReproduceProceed"
    @debug-reproduce-dismiss="composer.handleDebugReproduceDismiss()"
    @approve-run="composer.handleApproveRun()"
    @reject-run="composer.handleRejectRun()"
    @undo-plan-soft-switch="composer.undoPlanSoftSwitch()"
    @dismiss-plan-soft-switch="composer.dismissPlanSoftSwitch()"
    @accept-plan-soft-switch-offer="composer.acceptPlanSoftSwitchOffer()"
    @decline-plan-soft-switch-offer="composer.declinePlanSoftSwitchOffer()"
    @undo-teammate-route="composer.undoTeammateRoute()"
    @dismiss-teammate-route="composer.dismissTeammateRoute()"
  />
  <form
    class="agent-dock-composer"
    @submit="composer.handleSubmit"
    @dragover="composer.handleComposerDragOver"
    @dragleave="composer.handleComposerDragLeave"
    @drop="composer.handleComposerDrop"
  >
    <BriefingSurfaceFollowupPrompt />
    <div class="agent-dock-composer__shell" :class="composer.composerShellClasses.value">
      <div class="agent-dock-composer__card">
        <AgentDockComposerAccessBanner
          v-if="composer.composerAccessBanner.value"
          :banner="composer.composerAccessBanner.value"
        />
        <AgentDockComposerInput
          :set-input-ref="composer.setInputRef"
          :draft="composer.composerDraftModel.value"
          :composer-mode="composer.composerMode.value"
          :operator-persona-name="composer.OPERATOR_PERSONA_NAME"
          :placeholder="composer.composerPlaceholder.value"
          :workspace-selected="Boolean(composer.shell.currentWorkspace)"
          :attachment-chips="composer.attachmentChips.value"
          :composer-images="composer.composerImages.value"
          :queue-items="composer.shell.ideComposerQueue"
          :queue-summary="composer.shell.ideComposerQueueSummary"
          :activity-chips="composer.composerActivityChips.value"
          :composer-queue-hint="composer.composerQueueHint.value"
          :show-composer-resume="composer.showComposerResume.value"
          :composer-resume-label="composer.composerResumeLabel.value"
          :show-composer-steer="composer.showComposerSteer.value"
          :show-composer-stop="composer.showComposerStop.value"
          :can-submit-composer="composer.canSubmitComposer.value"
          :composer-submit-label="composer.composerSubmitLabel.value"
          :access-tone="composer.composerAccessToneValue.value"
          :command-mutation-state="composer.shell.commandMutationState"
          :run-mutation-state="composer.shell.runMutationState"
          :kairo-pending="composer.kairoPending.value"
          :speech-capture-supported="composer.speechCapture.supported"
          :speech-capturing="composer.speechCapture.capturing.value"
          :privacy-mode="composer.shell.operatorPresenceSettings.privacy_mode"
          :typeahead-open="composer.typeaheadOpen.value"
          :typeahead-caption="composer.typeaheadCaption.value"
          :typeahead-loading="composer.typeaheadLoading.value"
          :typeahead-rows="composer.typeaheadRows.value"
          :typeahead-selected-index="composer.typeaheadSelectedIndex.value"
          @update:draft="composer.updateComposerDraft"
          @remove-chip="composer.removeChip"
          @open-image="composer.openComposerImage"
          @remove-image="composer.removeComposerImage"
          @edit-queued="composer.editQueuedMessage"
          @remove-queued="composer.removeQueuedMessage"
          @steer-queued="composer.handleSteerQueuedMessage"
          @sync-height="composer.syncComposerHeight"
          @sync-typeahead="composer.syncTypeaheadFromComposer()"
          @typeahead-select="composer.applyTypeaheadRow"
          @typeahead-hover="composer.selectTypeaheadIndex"
          @keydown="composer.handleComposerKeydown"
          @paste="composer.handleComposerPaste"
          @reveal-terminal="composer.revealComposerTerminalPanel"
          @resume="composer.handleResumeRun"
          @steer="composer.handleSteer"
          @toggle-voice="composer.toggleVoiceCapture"
          @stop="composer.handleStopRun"
        >
          <template #toolbar>
            <AgentDockComposerToolbar
              v-bind="toolbarProps"
              @toggle-section="composer.toggleSection"
              @toggle-context="composer.toggleContext"
              @attach-files-media="composer.attachFilesMedia"
              @convert-to-instructions="composer.convertDraftToInstructions"
              @toggle-runtime-targets="composer.toggleRuntimeTargetsPanel"
              @select-runtime-target="composer.selectRuntimeTarget"
              @select-composer-model="composer.selectComposerModel"
              @select-manage-model="composer.selectManageModelRow"
              @open-add-models="composer.openAddModelsPanel"
              @close-add-models="composer.closeAddModelsPanel"
              @auto-toggle-click="composer.onAutoToggleClick"
              @update:model-search-query="composer.modelSearchQuery.value = $event"
              @select-mode="composer.selectMode"
              @request-full-access="composer.requestFullAccess"
              @switch-consultative="composer.switchToConsultativeAccess"
              @request-sandbox-session="composer.requestSandboxSession"
              @disable-sandbox-session="composer.disableSandboxSessionAccess"
              @open-vault="composer.openVaultSurface"
            />
          </template>
        </AgentDockComposerInput>
      </div>
    </div>
    <AgentDockKairoComposerFooter
      :composer-mode="composer.composerMode.value"
      :operator-persona-name="composer.OPERATOR_PERSONA_NAME"
      :kairo-conversation-reply="composer.kairoConversationReply.value"
      :kairo-conversation-error="composer.kairoConversationError.value"
      :command-mutation-error="composer.shell.commandMutationError"
      :run-mutation-error="composer.shell.runMutationError"
      :workspace-selected="Boolean(composer.shell.currentWorkspace)"
    />
  </form>
</template>
