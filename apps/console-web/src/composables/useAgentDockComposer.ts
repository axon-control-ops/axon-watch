import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue';

import {
  FULL_ACCESS_CONSENT_LINES,
} from '../lib/agent-dock-activity-view';
import { agentExecutionAccessHint } from '../lib/agent-execution-access-prefs';
import { resizeCommandComposer } from '../lib/command-composer-autosize';
import {
  resolveActiveIdeAgentMessage,
} from '../lib/ide-agent-center-view';
import { summarizeIdeAgentActivity } from '../lib/ide-agent-activity-view';
import {
  filterMcpToolsForComposerMode,
  mcpToolDetail,
} from '../lib/composer-mcp-tools-view';
import {
  kairoConversationError,
  kairoConversationReply,
} from '../features/kairo-conversation/kairo-conversation-state';
import { useKairoConversation } from '../features/kairo-conversation/use-kairo-conversation';
import { OPERATOR_PERSONA_NAME } from '../lib/operator-persona-name';
import { useShellStore } from '../stores/shell';
import { useComposerActions } from './agent-dock/use-composer-actions';
import { useComposerContext } from './agent-dock/use-composer-context';
import { useComposerHistory } from './agent-dock/use-composer-history';
import { useComposerImages } from './agent-dock/use-composer-images';
import {
  MODE_OPTIONS,
  useComposerMenus,
  type ComposerMode,
} from './agent-dock/use-composer-menus';
import { useComposerModelRuntime } from './agent-dock/use-composer-model-runtime';

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

  function setInputRef(el: HTMLTextAreaElement | null): void {
    inputRef.value = el;
  }

  const composerMode = ref<ComposerMode>(
    (shell.runtimeSummary?.runtime_identity.mode_default as ComposerMode) || 'agent',
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
    contextActiveFile,
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
    handleComposerPaste,
    handleComposerDragOver,
    handleComposerDragLeave,
    handleComposerDrop,
    removeComposerImage,
    disposeComposerImagesPersistTimer,
    revokeAllComposerImagePreviews,
  } = useComposerImages();

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
    currentRuntimeTarget,
    extraPinnedRows,
    onAutoToggleClick,
    openAddModelsPanel,
    openVaultSurface,
    runtimeDetail,
    runtimeHint,
    runtimeLabel,
    runtimeStatusLine,
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
    handleRejectRun,
    handleResumeRun,
    handleStopRun,
    handleSubmit,
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
  });

  const composerAgentBusy = computed(() => shell.composerAgentBusy);
  const composerPlaceholder = computed(() => {
    if (composerMode.value === 'kairo') {
      return `Talk to ${OPERATOR_PERSONA_NAME} — answers are spoken aloud`;
    }
    if (composerAgentBusy.value && composerMode.value === 'agent') {
      return 'Queue a follow-up or steer with Ctrl+Enter…';
    }
    if (composerMode.value === 'plan') {
      return 'Plan your approach, constraints, and verification path…';
    }
    if (composerMode.value === 'ask') {
      return 'Ask about this workspace, file, or runtime…';
    }
    return 'Describe what you want to build or change…';
  });
  const mcpToolsForMode = computed(() => {
    if (composerMode.value === 'kairo') {
      return [];
    }
    return filterMcpToolsForComposerMode(shell.runtimeMcpTools, composerMode.value);
  });
  const showComposerResume = computed(() => shell.canResumeIdeAgentRun);
  const showComposerStop = computed(
    () => shell.canStopIdeAgentRun && composerMode.value !== 'kairo',
  );
  const composerQueueHint = computed(() => {
    if (!composerAgentBusy.value || composerMode.value !== 'agent') {
      return '';
    }
    const steerKey = typeof navigator !== 'undefined' && /Mac/i.test(navigator.platform)
      ? '⌘'
      : 'Ctrl';
    return `Enter queues · ${steerKey}+Enter steers`;
  });
  const composerActivitySummary = computed(() => {
    if (!shell.agentStreamActive && !shell.composerAgentBusy) {
      return null;
    }
    const message = resolveActiveIdeAgentMessage(
      shell.threadMessages,
      shell.agentStreamActive,
      shell.agentStreamMessageId,
    );
    if (!message) {
      return null;
    }
    return summarizeIdeAgentActivity(message.content);
  });
  const composerActivityChips = computed(() =>
    composerMode.value === 'kairo' ? [] : composerActivitySummary.value?.chips ?? [],
  );
  const composerDraftModel = computed({
    get: () => (composerMode.value === 'kairo' ? kairoDraft.value : shell.ideComposerDraft),
    set: (value: string) => {
      if (composerMode.value === 'kairo') {
        kairoDraft.value = value;
        return;
      }
      shell.ideComposerDraft = value;
    },
  });
  const canSubmitComposer = computed(() => {
    if (composerMode.value === 'kairo') {
      return kairoCanSubmit.value && Boolean(shell.currentWorkspace);
    }
    return shell.canSubmitIdeComposer;
  });
  const composerSubmitLabel = computed(() => {
    if (composerMode.value === 'kairo') {
      return kairoPending.value ? `Asking ${OPERATOR_PERSONA_NAME}` : `Ask ${OPERATOR_PERSONA_NAME}`;
    }
    if (shell.commandMutationState === 'submitting') {
      return 'Sending command';
    }
    if (composerAgentBusy.value && composerMode.value === 'agent') {
      return 'Queue message';
    }
    return 'Send command';
  });
  const composerShellClasses = computed(() => ({
    [`agent-dock-composer__shell--${composerMode.value}`]: true,
    'agent-dock-composer__shell--full-access': isFullAccessAgent.value,
    'agent-dock-composer__shell--drag-over': composerDragOver.value,
  }));

  function handleDocumentClick(): void {
    closeMenus();
  }

  watch(
    () => shell.ideComposerDraft,
    () => {
      const fromHistory = applyingHistoryDraft.value;
      if (fromHistory) {
        applyingHistoryDraft.value = false;
      } else if (composerHistoryIndex.value >= 0) {
        composerHistoryIndex.value = -1;
        composerHistoryScratch.value = '';
      }
      void nextTick(syncComposerHeight);
      syncContextFromDraft();
    },
  );

  watch(
    () => shell.currentWorkspace?.workspace_id ?? null,
    (workspaceId) => {
      loadComposerHistoryForWorkspace(workspaceId);
      loadComposerImagesForWorkspace(workspaceId);
    },
    { immediate: true },
  );

  watch(
    () => shell.commandFocusToken,
    () => {
      void nextTick(() => {
        syncComposerHeight();
        inputRef.value?.focus();
      });
    },
  );

  onMounted(() => {
    syncComposerHeight();
    syncContextFromDraft();
    document.addEventListener('click', handleDocumentClick);
  });

  onUnmounted(() => {
    document.removeEventListener('click', handleDocumentClick);
    disposeComposerImagesPersistTimer();
    void persistCurrentComposerImages();
    revokeAllComposerImagePreviews();
  });

  return {
    FULL_ACCESS_CONSENT_LINES,
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
    composerAgentBusy,
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
    currentRuntimeTarget,
    enlargedComposerImage,
    executionAccessHint,
    extraPinnedRows,
    fullAccessConsentChecked,
    handleApproveRun,
    handleComposerDragLeave,
    handleComposerDragOver,
    handleComposerDrop,
    handleComposerImageLightboxKeydown,
    handleComposerKeydown,
    handleComposerPaste,
    handleRejectRun,
    handleResumeRun,
    handleStopRun,
    handleSubmit,
    hasTerminalSnippet,
    inputRef,
    setInputRef,
    isFullAccessAgent,
    kairoCanSubmit,
    kairoConversationError,
    kairoConversationReply,
    kairoDraft,
    kairoPending,
    mcpToolDetail,
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
    runtimeStatusLine,
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
    cancelFullAccessConsent,
  };
}
