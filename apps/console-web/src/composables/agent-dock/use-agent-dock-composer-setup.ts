import { ref } from 'vue';

import { resizeCommandComposer } from '../../lib/command-composer-autosize';
import { useKairoConversation } from '../../features/kairo-conversation/use-kairo-conversation';
import { useShellStore } from '../../stores/shell';
import {
  useComposerActions,
  type PlanSoftSwitchNotice,
} from './use-composer-actions';
import { useComposerContext } from './use-composer-context';
import { useComposerDisplayState } from './use-composer-display-state';
import { useComposerHistory } from './use-composer-history';
import { useComposerImages } from './use-composer-images';
import {
  useComposerMenus,
  type ComposerMode,
} from './use-composer-menus';
import { useComposerModelRuntime } from './use-composer-model-runtime';
import { useComposerWorkspaceSync } from './use-composer-workspace-sync';
import { readWorkspaceComposerMode } from '../../lib/composer-mode-prefs';
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
    toggleContext,
    removeChip,
    syncContextFromDraft,
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
    shell,
    inputRef,
    syncComposerHeight,
    clearComposerImages,
    composerImages,
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

  const {
    dismissPlanSoftSwitch,
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
  } = useComposerActions({
    shell,
    composerMode,
    inputRef,
    kairoDraft,
    composerImages,
    composerHistory,
    composerHistoryIndex,
    submitKairoTurn,
    recordComposerHistoryIfSent,
    handleHistory,
    speechCapture,
    startVoiceCapture,
    stopVoiceCapture,
    planSoftSwitchNotice,
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
  });

  useComposerWorkspaceSync({
    shell,
    composerMode,
    defaultComposerMode,
    inputRef,
    applyingHistoryDraft,
    composerHistoryIndex,
    composerHistoryScratch,
    planSoftSwitchNotice,
    closeMenus,
    syncComposerHeight,
    syncContextFromDraft,
    loadComposerHistoryForWorkspace,
    loadComposerImagesForWorkspace,
    disposeComposerImagesPersistTimer,
    persistCurrentComposerImages,
    revokeAllComposerImagePreviews,
  });

  return buildAgentDockComposerApi({
    activeMode,
    attachmentChips,
    autoModelRow,
    autoToggleChecked,
    canSubmitComposer,
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
    syncComposerHeight,
    toggleContext,
    toggleRuntimeTargetsPanel,
    toggleSection,
    toggleVoiceCapture,
    undoPlanSoftSwitch,
    cancelFullAccessConsent,
  });
}
