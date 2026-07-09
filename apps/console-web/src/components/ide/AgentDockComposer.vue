<script setup lang="ts">
import BriefingSurfaceFollowupPrompt from '../../features/kairo-conversation/BriefingSurfaceFollowupPrompt.vue';
import OperatorPersonaMark from '../OperatorPersonaMark.vue';
import { useAgentDockComposer } from '../../composables/useAgentDockComposer';
import AgentDockComposerImageLightbox from './agent-dock/AgentDockComposerImageLightbox.vue';
import AgentDockComposerInput from './agent-dock/AgentDockComposerInput.vue';
import AgentDockComposerToolbar from './agent-dock/AgentDockComposerToolbar.vue';
import AgentDockFullAccessConsent from './agent-dock/AgentDockFullAccessConsent.vue';

const {
  MODE_OPTIONS,
  OPERATOR_PERSONA_NAME,
  activeMode,
  attachmentChips,
  autoModelRow,
  autoToggleChecked,
  canSubmitComposer,
  cancelFullAccessConsent,
  closeAddModelsPanel,
  closeComposerImageLightbox,
  composerActivityChips,
  composerDraftModel,
  composerImages,
  composerMode,
  composerPlaceholder,
  composerPickerRows,
  composerQueueHint,
  composerShellClasses,
  composerSubmitLabel,
  confirmFullAccessConsent,
  contextActiveFile,
  contextIde,
  contextPinned,
  contextSelection,
  contextTerminal,
  contextWorkspace,
  cursorAuthLine,
  cursorCatalogCount,
  cursorCatalogStatus,
  cursorCatalogTotal,
  cursorManageRows,
  cursorStaleWarning,
  enlargedComposerImage,
  executionAccessHint,
  extraPinnedRows,
  fullAccessConsentChecked,
  handleApproveRun,
  handleComposerDragLeave,
  handleComposerDragOver,
  handleComposerDrop,
  handleComposerKeydown,
  handleComposerPaste,
  handleRejectRun,
  handleResumeRun,
  handleStopRun,
  handleSubmit,
  hasTerminalSnippet,
  inputRef,
  isFullAccessAgent,
  kairoConversationError,
  kairoConversationReply,
  kairoPending,
  mcpToolsForMode,
  modeButtonLabel,
  modelSearchQuery,
  onAutoToggleClick,
  openAddModelsPanel,
  openComposerImage,
  openVaultSurface,
  removeChip,
  removeComposerImage,
  removeQueuedMessage,
  requestFullAccess,
  revealComposerTerminalPanel,
  runtimeDetail,
  runtimeHint,
  runtimeLabel,
  runtimeTargets,
  selectComposerModel,
  selectManageModelRow,
  selectMode,
  selectRuntimeTarget,
  selectedModelId,
  selectedModelLabel,
  selectedRuntimeSummary,
  selectionChipLabel,
  shell,
  showAddModelsEntry,
  showAddModelsPanel,
  showApprovalBanner,
  showComposerResume,
  showComposerStop,
  showContextMenu,
  showCursorCatalog,
  showExtraPinnedRows,
  showFullAccessConsent,
  showModeMenu,
  showModelMenu,
  showRuntimeTargetsPanel,
  showToolsMenu,
  showVaultAction,
  speechCapture,
  switchToConsultativeAccess,
  syncComposerHeight,
  toggleContext,
  toggleRuntimeTargetsPanel,
  toggleSection,
  toggleVoiceCapture,
} = useAgentDockComposer();

function setInputRef(el: HTMLTextAreaElement | null): void {
  inputRef.value = el;
}
</script>

<template>
  <AgentDockFullAccessConsent
    :show="showFullAccessConsent"
    :checked="fullAccessConsentChecked"
    @update:checked="fullAccessConsentChecked = $event"
    @cancel="cancelFullAccessConsent"
    @confirm="confirmFullAccessConsent"
  />

  <AgentDockComposerImageLightbox
    :image="enlargedComposerImage"
    @close="closeComposerImageLightbox"
  />

  <form
    class="agent-dock-composer"
    @submit="handleSubmit"
    @dragover="handleComposerDragOver"
    @dragleave="handleComposerDragLeave"
    @drop="handleComposerDrop"
  >
    <BriefingSurfaceFollowupPrompt />
    <div
      v-if="showApprovalBanner"
      class="agent-dock-composer__approval-banner"
      role="status"
    >
      <p class="agent-dock-composer__approval-copy">
        Full Access is waiting for approval before tools can edit files or run commands.
      </p>
      <div class="agent-dock-composer__approval-actions">
        <button
          type="button"
          class="agent-dock-composer__approval-btn agent-dock-composer__approval-btn--approve"
          :disabled="!shell.canApproveIdeAgentRun"
          @click="handleApproveRun"
        >
          Approve
        </button>
        <button
          type="button"
          class="agent-dock-composer__approval-btn agent-dock-composer__approval-btn--reject"
          :disabled="shell.runMutationPending"
          @click="handleRejectRun"
        >
          Reject
        </button>
      </div>
    </div>
    <div
      class="agent-dock-composer__shell"
      :class="composerShellClasses"
    >
      <div class="agent-dock-composer__card">
        <AgentDockComposerInput
          :set-input-ref="setInputRef"
          :draft="composerDraftModel"
          :composer-mode="composerMode"
          :operator-persona-name="OPERATOR_PERSONA_NAME"
          :placeholder="composerPlaceholder"
          :workspace-selected="Boolean(shell.currentWorkspace)"
          :attachment-chips="attachmentChips"
          :composer-images="composerImages"
          :queue-items="shell.ideComposerQueue"
          :queue-summary="shell.ideComposerQueueSummary"
          :activity-chips="composerActivityChips"
          :composer-queue-hint="composerQueueHint"
          :show-composer-resume="showComposerResume"
          :show-composer-stop="showComposerStop"
          :can-submit-composer="canSubmitComposer"
          :composer-submit-label="composerSubmitLabel"
          :command-mutation-state="shell.commandMutationState"
          :run-mutation-state="shell.runMutationState"
          :kairo-pending="kairoPending"
          :speech-capture-supported="speechCapture.supported"
          :speech-capturing="speechCapture.capturing.value"
          :privacy-mode="shell.operatorPresenceSettings.privacy_mode"
          @update:draft="composerDraftModel = $event"
          @remove-chip="removeChip"
          @open-image="openComposerImage"
          @remove-image="removeComposerImage"
          @remove-queued="removeQueuedMessage"
          @sync-height="syncComposerHeight"
          @keydown="handleComposerKeydown"
          @paste="handleComposerPaste"
          @reveal-terminal="revealComposerTerminalPanel"
          @resume="handleResumeRun"
          @toggle-voice="toggleVoiceCapture"
          @stop="handleStopRun"
        >
          <template #toolbar>
            <AgentDockComposerToolbar
              :show-context-menu="showContextMenu"
              :show-tools-menu="showToolsMenu"
              :show-model-menu="showModelMenu"
              :show-mode-menu="showModeMenu"
              :show-add-models-panel="showAddModelsPanel"
              :show-runtime-targets-panel="showRuntimeTargetsPanel"
              :show-add-models-entry="showAddModelsEntry"
              :show-extra-pinned-rows="showExtraPinnedRows"
              :show-cursor-catalog="showCursorCatalog"
              :show-vault-action="showVaultAction"
              :attachment-chips="attachmentChips"
              :mcp-tools-for-mode="mcpToolsForMode"
              :composer-mode="composerMode"
              :mode-options="MODE_OPTIONS"
              :mode-button-label="modeButtonLabel"
              :active-mode="activeMode"
              :is-full-access-agent="isFullAccessAgent"
              :execution-access-hint="executionAccessHint"
              :context-workspace="contextWorkspace"
              :context-active-file="contextActiveFile"
              :context-selection="contextSelection"
              :context-terminal="contextTerminal"
              :context-ide="contextIde"
              :context-pinned="contextPinned"
              :has-terminal-snippet="hasTerminalSnippet"
              :selection-chip-label="selectionChipLabel"
              :runtime-detail="runtimeDetail"
              :runtime-label="runtimeLabel"
              :selected-runtime-summary="selectedRuntimeSummary"
              :runtime-targets="runtimeTargets"
              :selected-model-id="selectedModelId"
              :selected-model-label="selectedModelLabel"
              :auto-model-row="autoModelRow"
              :auto-toggle-checked="autoToggleChecked"
              :composer-picker-rows="composerPickerRows"
              :extra-pinned-rows="extraPinnedRows"
              :cursor-catalog-total="cursorCatalogTotal"
              :cursor-catalog-status="cursorCatalogStatus"
              :cursor-auth-line="cursorAuthLine"
              :cursor-stale-warning="cursorStaleWarning"
              :cursor-manage-rows="cursorManageRows"
              :cursor-catalog-count="cursorCatalogCount"
              :model-search-query="modelSearchQuery"
              :runtime-hint="runtimeHint"
              @toggle-section="toggleSection"
              @toggle-context="toggleContext"
              @toggle-runtime-targets="toggleRuntimeTargetsPanel"
              @select-runtime-target="selectRuntimeTarget"
              @select-composer-model="selectComposerModel"
              @select-manage-model="selectManageModelRow"
              @open-add-models="openAddModelsPanel"
              @close-add-models="closeAddModelsPanel"
              @auto-toggle-click="onAutoToggleClick"
              @update:model-search-query="modelSearchQuery = $event"
              @select-mode="selectMode"
              @request-full-access="requestFullAccess"
              @switch-consultative="switchToConsultativeAccess"
              @open-vault="openVaultSurface"
            />
          </template>
        </AgentDockComposerInput>
      </div>
    </div>

    <div v-if="composerMode === 'kairo' && kairoConversationReply" class="agent-dock-composer__kairo-reply">
      <span class="agent-dock-composer__kairo-reply-label">
        <OperatorPersonaMark size="xs" />
        <span>Reply</span>
      </span>
      <p class="agent-dock-composer__kairo-reply-text">{{ kairoConversationReply }}</p>
    </div>
    <p v-if="composerMode === 'kairo' && kairoConversationError" class="agent-dock-composer__error" role="alert">
      {{ kairoConversationError }}
    </p>
    <p v-else-if="composerMode === 'kairo'" class="agent-dock-composer__kairo-hint">
      Tap header {{ OPERATOR_PERSONA_NAME }} to pause or continue · Esc stops speech · Mic barge-in
    </p>

    <p v-if="!shell.currentWorkspace" class="agent-dock-composer__empty">
      Select a workspace to send commands.
    </p>
    <p v-if="shell.commandMutationError" class="agent-dock-composer__error">
      {{ shell.commandMutationError }}
    </p>
    <p v-if="shell.runMutationError" class="agent-dock-composer__error">
      {{ shell.runMutationError }}
    </p>
  </form>
</template>
