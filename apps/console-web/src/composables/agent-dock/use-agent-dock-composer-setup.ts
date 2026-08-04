import { computed, nextTick, ref } from 'vue';

import { resizeCommandComposer } from '../../lib/command-composer-autosize';
import { useKairoConversation } from '../../features/kairo-conversation/use-kairo-conversation';
import { useShellStore } from '../../stores/shell';
import { useComposerActions, type PlanSoftSwitchNotice } from './use-composer-actions';
import { useComposerContext } from './use-composer-context';
import { useComposerDisplayState } from './use-composer-display-state';
import { useComposerHistory } from './use-composer-history';
import { useComposerImages } from './use-composer-images';
import { useComposerMenus, type ComposerMode } from './use-composer-menus';
import { useComposerModelRuntime } from './use-composer-model-runtime';
import { useComposerTypeahead } from './use-composer-typeahead';
import { useComposerWorkspaceSync } from './use-composer-workspace-sync';
import { readWorkspaceComposerMode } from '../../lib/composer-mode-prefs';
import { persistIdeComposerDraft } from '../../lib/ide-composer-draft-prefs';
import { teammateRouteNotice } from '../../lib/teammate-route-notice';
import { buildAgentDockComposerApi } from './build-agent-dock-composer-api';

export function useAgentDockComposerSetup() {
  const shell = useShellStore();
  const {
    draft: kairoDraft,
    pending: kairoPending,
    canSubmit: kairoCanSubmit,
    submitTurn: submitKairoTurn,
    speechCapture,
    startVoiceCapture,
    stopVoiceCapture,
  } = useKairoConversation();
  const inputRef = ref<HTMLTextAreaElement | null>(null);
  const dismissedDebugReproduceMessageId = ref<string | null>(null);
  const planSoftSwitchNotice = ref<PlanSoftSwitchNotice | null>(null);
  function setInputRef(el: HTMLTextAreaElement | null): void {
    inputRef.value = el;
  }

  const defaultComposerMode =
    (shell.runtimeSummary?.runtime_identity.mode_default as ComposerMode) || 'agent';
  const composerMode = ref<ComposerMode>(
    readWorkspaceComposerMode(
      shell.currentWorkspace?.workspace_id,
      sessionStorage,
      shell.activeIdeThreadId,
    ) ?? defaultComposerMode,
  );

  const menus = useComposerMenus(shell, { composerMode });
  const {
    activeMode,
    cancelFullAccessConsent,
    cancelSandboxConsent,
    closeMenus,
    confirmFullAccessConsent,
    confirmSandboxConsent,
    disableSandboxSessionAccess,
    executionAccessHint,
    fullAccessConsentChecked,
    isFullAccessAgent,
    modeButtonLabel,
    modeButtonTitle,
    modelSearchQuery,
    requestFullAccess,
    requestSandboxSession,
    sandboxConsentChecked,
    sandboxEnvForced,
    sandboxHint,
    sandboxLabel,
    sandboxSessionEnabled,
    sandboxSessionError,
    sandboxSessionPending,
    selectMode,
    showAddModelsPanel,
    showApprovalBanner,
    showContextMenu,
    showFullAccessConsent,
    showModeMenu,
    showModelMenu,
    showRuntimeTargetsPanel,
    showSandboxConsent,
    showToolsMenu,
    switchToConsultativeAccess,
    toggleSection,
  } = menus;

  const {
    contextWorkspace,
    contextSelection,
    contextTerminal,
    contextIde,
    contextPinned,
    hasTerminalSnippet,
    selectionChipLabel,
    attachmentChips,
    skillAttachments,
    toggleContext,
    removeChip,
    syncContextFromDraft,
    upsertSkillAttachment,
    clearSkillAttachments,
    withSkillTokensForSubmit,
  } = useComposerContext(shell);

  const images = useComposerImages();
  const {
    composerImages,
    enlargedComposerImage,
    composerDragOver,
    clearComposerImages,
    persistCurrentComposerImages,
    loadComposerImagesForWorkspace,
    openComposerImage,
    closeComposerImageLightbox,
    handleComposerPaste,
    handleComposerDragOver,
    handleComposerDragLeave,
    handleComposerDrop,
    removeComposerImage,
    disposeComposerImagesPersistTimer,
    revokeAllComposerImagePreviews,
  } = images;

  function attachFilesMedia(): void {
    images.openComposerAttachmentPicker();
    closeMenus();
  }

  function syncComposerHeight(): void {
    if (!inputRef.value) return;
    resizeCommandComposer(inputRef.value, { compact: true });
  }

  const {
    composerHistory,
    composerHistoryIndex,
    composerHistoryScratch,
    applyingHistoryDraft,
    loadComposerHistoryForWorkspace,
    handleHistory,
    recordComposerHistoryIfSent,
  } = useComposerHistory({
    inputRef,
    syncComposerHeight,
    clearComposerImages,
    composerImages,
    getDraft: () =>
      composerMode.value === 'kairo' ? kairoDraft.value : shell.ideComposerDraft,
    setDraft: (value) => {
      if (composerMode.value === 'kairo') {
        kairoDraft.value = value;
        return;
      }
      shell.ideComposerDraft = value;
    },
  });

  const {
    autoModelRow,
    autoToggleChecked,
    closeAddModelsPanel,
    composerPickerRows,
    cursorAuthLine,
    cursorCatalogCount,
    cursorCatalogStatus,
    cursorCatalogTotal,
    cursorManageRows,
    cursorStaleWarning,
    extraPinnedRows,
    onAutoToggleClick,
    openAddModelsPanel,
    openVaultSurface,
    runtimeDetail,
    runtimeFamilyLabel,
    runtimeHint,
    runtimeLabel,
    runtimeTargets,
    selectComposerModel,
    selectManageModelRow,
    selectRuntimeTarget,
    selectedModelId,
    selectedModelLabel,
    selectedRuntimeSummary,
    showAddModelsEntry,
    showCursorCatalog,
    showExtraPinnedRows,
    showVaultAction,
    toggleRuntimeTargetsPanel,
  } = useComposerModelRuntime(shell, {
    showAddModelsPanel,
    showRuntimeTargetsPanel,
    modelSearchQuery,
    closeMenus,
  });

  const typeahead = useComposerTypeahead({
    shell,
    composerMode,
    inputRef,
    getDraft: () =>
      composerMode.value === 'kairo' ? kairoDraft.value : shell.ideComposerDraft,
    setDraft: (value) => {
      if (composerMode.value === 'kairo') {
        kairoDraft.value = value;
        return;
      }
      shell.ideComposerDraft = value;
    },
    closeToolbarMenus: closeMenus,
    attachSkill: upsertSkillAttachment,
  });

  const {
    typeaheadOpen,
    typeaheadKind,
    typeaheadRows,
    typeaheadCaption,
    typeaheadEmptyHint,
    typeaheadSelectedIndex,
    typeaheadLoading,
    closeTypeahead,
    syncTypeaheadFromComposer,
    handleTypeaheadKeydown,
    applyTypeaheadRow,
    selectTypeaheadIndex,
  } = typeahead;

  const baseToggleSection = toggleSection;
  function toggleSectionWithTypeahead(
    section: 'context' | 'tools' | 'model' | 'mode',
  ): void {
    closeTypeahead();
    baseToggleSection(section);
  }

  const {
    acceptPlanSoftSwitchOffer,
    declinePlanSoftSwitchOffer,
    dismissPlanSoftSwitch,
    dismissTeammateRoute,
    handleApproveRun,
    handleComposerKeydown,
    handleDebugReproduceProceed,
    handleRejectRun,
    handleResumeRun,
    handleSteer,
    handleSteerQueuedMessage,
    handleStopRun,
    handleSubmit,
    editQueuedMessage,
    removeQueuedMessage,
    revealComposerTerminalPanel,
    toggleVoiceCapture,
    undoPlanSoftSwitch,
    undoTeammateRoute,
  } = useComposerActions({
    shell,
    composerMode,
    inputRef,
    kairoDraft,
    composerImages,
    composerHistory,
    composerHistoryIndex,
    dismissedDebugReproduceMessageId,
    submitKairoTurn,
    recordComposerHistoryIfSent,
    handleHistory,
    speechCapture,
    startVoiceCapture,
    stopVoiceCapture,
    planSoftSwitchNotice,
    teammateRouteNotice,
    handleTypeaheadKeydown,
    withSkillTokensForSubmit,
    clearSkillAttachments,
    onDebugReproduceProceed: (messageId) => {
      dismissedDebugReproduceMessageId.value = messageId;
    },
  });

  const {
    composerAccessBanner,
    composerAccessToneValue,
    composerActivityChips,
    composerDraftModel,
    canConvertInstructions,
    convertDraftToInstructions,
    composerPlaceholder,
    composerQueueHint,
    composerResumeLabel,
    composerShellClasses,
    composerSubmitLabel,
    canSubmitComposer,
    debugReproduceRequest,
    handleDebugReproduceDismiss,
    mcpToolsForMode,
    showComposerResume,
    showComposerSteer,
    showComposerStop,
    showDebugReproduceBanner,
  } = useComposerDisplayState({
    shell,
    composerMode,
    composerDragOver,
    isFullAccessAgent,
    sandboxSessionEnabled,
    kairoDraft,
    kairoCanSubmit,
    kairoPending,
    dismissedDebugReproduceMessageId,
    syncComposerHeight,
    skillAttachmentCount: computed(() => skillAttachments.value.length),
  });

  function updateComposerDraft(value: string): void {
    composerDraftModel.value = value;
    void syncTypeaheadFromComposer();
  }

  function clearComposerDraft(): void {
    composerDraftModel.value = '';
    if (composerMode.value !== 'kairo') {
      persistIdeComposerDraft(
        shell.currentWorkspace?.workspace_id ?? null,
        '',
        shell.activeIdeThreadId || null,
      );
    }
    closeTypeahead();
    void nextTick(syncComposerHeight);
  }

  useComposerWorkspaceSync({
    shell,
    composerMode,
    defaultComposerMode,
    inputRef,
    applyingHistoryDraft,
    composerHistoryIndex,
    composerHistoryScratch,
    planSoftSwitchNotice,
    teammateRouteNotice,
    closeMenus: () => {
      closeMenus();
      closeTypeahead();
    },
    syncComposerHeight,
    syncContextFromDraft,
    getActiveDraft: () =>
      composerMode.value === 'kairo' ? kairoDraft.value : shell.ideComposerDraft,
    loadComposerHistoryForWorkspace,
    loadComposerImagesForWorkspace,
    disposeComposerImagesPersistTimer,
    persistCurrentComposerImages,
    revokeAllComposerImagePreviews,
  });

  return buildAgentDockComposerApi({
    activeMode,
    applyTypeaheadRow,
    attachmentChips,
    autoModelRow,
    autoToggleChecked,
    canSubmitComposer,
    clearComposerDraft,
    closeAddModelsPanel,
    closeComposerImageLightbox,
    composerAccessBanner,
    composerAccessToneValue,
    composerActivityChips,
    composerDraftModel,
    canConvertInstructions,
    convertDraftToInstructions,
    composerImages,
    composerMode,
    composerPlaceholder,
    composerPickerRows,
    composerQueueHint,
    composerShellClasses,
    composerSubmitLabel,
    cancelSandboxConsent,
    confirmFullAccessConsent,
    confirmSandboxConsent,
    disableSandboxSessionAccess,
    attachFilesMedia,
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
    debugReproduceRequest,
    dismissPlanSoftSwitch,
    dismissTeammateRoute,
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
    handleDebugReproduceDismiss,
    handleDebugReproduceProceed,
    handleRejectRun,
    handleResumeRun,
    handleSteer,
    handleSteerQueuedMessage,
    handleStopRun,
    handleSubmit,
    hasTerminalSnippet,
    setInputRef,
    isFullAccessAgent,
    kairoPending,
    mcpToolsForMode,
    modeButtonLabel,
    modeButtonTitle,
    modelSearchQuery,
    onAutoToggleClick,
    openAddModelsPanel,
    openComposerImage,
    openVaultSurface,
    planSoftSwitchNotice,
    teammateRouteNotice,
    removeChip,
    removeComposerImage,
    editQueuedMessage,
    removeQueuedMessage,
    requestFullAccess,
    requestSandboxSession,
    revealComposerTerminalPanel,
    sandboxConsentChecked,
    sandboxEnvForced,
    sandboxHint,
    sandboxLabel,
    sandboxSessionEnabled,
    sandboxSessionError,
    sandboxSessionPending,
    runtimeDetail,
    runtimeFamilyLabel,
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
    composerResumeLabel,
    showComposerSteer,
    showComposerStop,
    showContextMenu,
    showCursorCatalog,
    showDebugReproduceBanner,
    showExtraPinnedRows,
    showFullAccessConsent,
    showSandboxConsent,
    showModeMenu,
    showModelMenu,
    showRuntimeTargetsPanel,
    showToolsMenu,
    showVaultAction,
    speechCapture,
    switchToConsultativeAccess,
    selectTypeaheadIndex,
    syncComposerHeight,
    syncTypeaheadFromComposer,
    toggleContext,
    toggleRuntimeTargetsPanel,
    toggleSection: toggleSectionWithTypeahead,
    toggleVoiceCapture,
    typeaheadCaption,
    typeaheadEmptyHint,
    typeaheadKind,
    typeaheadLoading,
    typeaheadOpen,
    typeaheadRows,
    typeaheadSelectedIndex,
    acceptPlanSoftSwitchOffer,
    declinePlanSoftSwitchOffer,
    undoPlanSoftSwitch,
    undoTeammateRoute,
    updateComposerDraft,
    cancelFullAccessConsent,
  });
}
