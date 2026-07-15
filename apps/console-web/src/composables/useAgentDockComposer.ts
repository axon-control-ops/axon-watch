import { nextTick, ref } from 'vue';

import { agentExecutionAccessHint } from '../lib/agent-execution-access-prefs';
import { resizeCommandComposer } from '../lib/command-composer-autosize';
import {
  kairoConversationError,
  kairoConversationReply,
} from '../features/kairo-conversation/kairo-conversation-state';
import { useKairoConversation } from '../features/kairo-conversation/use-kairo-conversation';
import { OPERATOR_PERSONA_NAME } from '../lib/operator-persona-name';
import { useShellStore } from '../stores/shell';
import { useComposerActions } from './agent-dock/use-composer-actions';
import { useComposerContext } from './agent-dock/use-composer-context';
import { useComposerDisplayState } from './agent-dock/use-composer-display-state';
import { useComposerHistory } from './agent-dock/use-composer-history';
import { useComposerImages } from './agent-dock/use-composer-images';
import {
  MODE_OPTIONS,
  useComposerMenus,
  type ComposerMode,
} from './agent-dock/use-composer-menus';
import { useComposerModelRuntime } from './agent-dock/use-composer-model-runtime';
import { useComposerWorkspaceSync } from './agent-dock/use-composer-workspace-sync';
import {
  readWorkspaceComposerMode,
} from '../lib/composer-mode-prefs';

export type { ComposerMode };
export { MODE_OPTIONS };
export function useAgentDockComposer() {
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

  function setInputRef(el: HTMLTextAreaElement | null): void {
    inputRef.value = el;
  }

  const defaultComposerMode =
    (shell.runtimeSummary?.runtime_identity.mode_default as ComposerMode) || 'agent';
  const composerMode = ref<ComposerMode>(
    readWorkspaceComposerMode(shell.currentWorkspace?.workspace_id) ?? defaultComposerMode,
  );

  const {
    activeMode,
    cancelFullAccessConsent,
    closeMenus,
    confirmFullAccessConsent,
    executionAccessHint,
    fullAccessConsentChecked,
    isFullAccessAgent,
    modeButtonLabel,
    modelSearchQuery,
    requestFullAccess,
    selectMode,
    showAddModelsPanel,
    showApprovalBanner,
    showContextMenu,
    showFullAccessConsent,
    showModeMenu,
    showModelMenu,
    showRuntimeTargetsPanel,
    showToolsMenu,
    switchToConsultativeAccess,
    toggleSection,
  } = useComposerMenus(shell, { composerMode });

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

  const {
    composerImages,
    enlargedComposerImage,
    composerDragOver,
    clearComposerImages,
    persistCurrentComposerImages,
    loadComposerImagesForWorkspace,
    openComposerImage,
    closeComposerImageLightbox,
    handleComposerImageLightboxKeydown,
    openComposerAttachmentPicker,
    handleComposerPaste,
    handleComposerDragOver,
    handleComposerDragLeave,
    handleComposerDrop,
    removeComposerImage,
    disposeComposerImagesPersistTimer,
    revokeAllComposerImagePreviews,
  } = useComposerImages();

  function attachFilesMedia(): void {
    openComposerAttachmentPicker();
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
    onDebugReproduceProceed: (messageId) => {
      dismissedDebugReproduceMessageId.value = messageId;
    },
  });

  const {
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
    closeMenus,
    syncComposerHeight,
    syncContextFromDraft,
    loadComposerHistoryForWorkspace,
    loadComposerImagesForWorkspace,
    disposeComposerImagesPersistTimer,
    persistCurrentComposerImages,
    revokeAllComposerImagePreviews,
  });

  return {
    MODE_OPTIONS,
    OPERATOR_PERSONA_NAME,
    activeMode,
    agentExecutionAccessHint,
    attachmentChips,
    autoModelRow,
    autoToggleChecked,
    canSubmitComposer,
    closeAddModelsPanel,
    closeComposerImageLightbox,
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
    confirmFullAccessConsent,
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
    editQueuedMessage,
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
    composerResumeLabel,
    showComposerSteer,
    showComposerStop,
    showContextMenu,
    showCursorCatalog,
    showDebugReproduceBanner,
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
    cancelFullAccessConsent,
  };
}
