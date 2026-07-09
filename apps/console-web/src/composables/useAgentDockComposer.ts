import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue';

import {
  FULL_ACCESS_CONSENT_LINES,
} from '../lib/agent-dock-activity-view';
import {
  agentExecutionAccessHint,
  agentExecutionAccessLabel,
} from '../lib/agent-execution-access-prefs';
import { navigateToAppSurface } from '../lib/app-surface-route';
import {
  runtimeNeedsVaultAction,
  runtimeVaultHint,
} from '../lib/agent-dock-runtime-view';
import {
  composerCursorAuthLine,
} from '../lib/runtime-auth-view';
import {
  cursorAutoModelDescription,
  cursorCatalogCountLabel,
  cursorCatalogModelRows,
  cursorCatalogStatusLabel,
  cursorComposerPickerRowsForActiveModel,
  cursorManageModelRows,
  cursorModelLabel,
  cursorPrimaryModelRows,
  cursorStaleModelWarning,
  isCursorAutoModel,
  isCursorComposerModel,
  type CursorCatalogRow,
  shouldShowCursorManualModelCatalog,
} from '../lib/cursor-catalog-view';
import { CURSOR_PICKER_COMPOSER_IDS, CURSOR_PICKER_DEFAULT_MODEL } from '../lib/cursor-picker-prefs';

import { resizeCommandComposer } from '../lib/command-composer-autosize';
import { shouldSteerAgentDockComposer, shouldSubmitAgentDockComposer } from '../lib/agent-dock-composer-input';
import {
  resolveActiveIdeAgentMessage,
} from '../lib/ide-agent-center-view';
import { summarizeIdeAgentActivity } from '../lib/ide-agent-activity-view';
import {
  shouldRecallNextAgentComposerHistory,
  shouldRecallPreviousAgentComposerHistory,
} from '../lib/agent-dock-composer-history';
import {
  filterMcpToolsForComposerMode,
  mcpToolDetail,
} from '../lib/composer-mcp-tools-view';
import {
  kairoConversationError,
  kairoConversationReply,
} from '../features/kairo-conversation/kairo-conversation-state';
import { useKairoConversation } from '../features/kairo-conversation/use-kairo-conversation';
import {
  clearBriefingSurfaceOffer,
  shouldOpenBriefingFromFollowup,
} from '../features/kairo-conversation/conversation-briefing-surface';
import { OPERATOR_PERSONA_NAME } from '../lib/operator-persona-name';
import { useShellStore } from '../stores/shell';
import { useComposerContext } from './agent-dock/use-composer-context';
import { useComposerHistory } from './agent-dock/use-composer-history';
import { useComposerImages } from './agent-dock/use-composer-images';

export type ComposerMode = 'agent' | 'plan' | 'ask' | 'kairo';

export const MODE_OPTIONS: Array<{
  key: ComposerMode;
  label: string;
  icon: string;
  hint: string;
}> = [
  { key: 'ask', label: 'Ask', icon: '◯', hint: 'Read-only answers, no tool execution' },
  { key: 'plan', label: 'Plan', icon: '◈', hint: 'Map steps before executing' },
  { key: 'agent', label: 'Agent', icon: '◎', hint: 'Agent loop with tools and approvals' },
  { key: 'kairo', label: OPERATOR_PERSONA_NAME, icon: '◉', hint: `Talk to ${OPERATOR_PERSONA_NAME} — spoken replies` },
];

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
const showContextMenu = ref(false);
const showToolsMenu = ref(false);
const showModelMenu = ref(false);
const showModeMenu = ref(false);
const showFullAccessConsent = ref(false);
const fullAccessConsentChecked = ref(false);
const showAddModelsPanel = ref(false);
const showRuntimeTargetsPanel = ref(false);
const modelSearchQuery = ref('');

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

const activeMode = computed(
  () => MODE_OPTIONS.find((option) => option.key === composerMode.value) ?? MODE_OPTIONS[2],
);
const runtimeTargets = computed(() => {
  const status = shell.runtimeStatus;
  if (!status) return [];
  return [...status.local, ...status.cloud];
});
const currentRuntimeTarget = computed(() => {
  const preferred = shell.selectedRuntimeTargetId;
  const status = shell.runtimeStatus;
  if (!status) return null;
  const records = [...status.local, ...status.cloud];
  if (preferred) {
    return records.find((record) => record.id === preferred) ?? records[0] ?? null;
  }
  const defaultRuntime = status.default_runtime;
  if (!defaultRuntime) return records[0] ?? null;
  return records.find((record) => record.id === defaultRuntime) ?? null;
});
const runtimeLabel = computed(() => {
  if (shell.composerRuntimeLabel) {
    return shell.composerRuntimeLabel;
  }
  const target = currentRuntimeTarget.value;
  if (target) {
    const scope = target.target_type === 'cloud' ? 'cloud' : 'local';
    return `${target.family} ${scope}`;
  }
  const identity = shell.runtimeSummary?.runtime_identity;
  if (!identity) return 'Runtime';
  return identity.model_name;
});
const runtimeDetail = computed(() => shell.composerRuntimeLabel || runtimeLabel.value);
const showCursorCatalog = computed(() => {
  const target = currentRuntimeTarget.value;
  return (target?.family ?? 'cursor') === 'cursor';
});
const selectedModelId = computed(() => shell.selectedComposerModel || 'auto');
const selectedModelLabel = computed(() =>
  cursorModelLabel(selectedModelId.value, shell.cursorCatalogRows),
);
const autoModelRow = computed(() =>
  shell.cursorCatalogRows.find((row) => row.id === 'auto') ?? {
    id: 'auto',
    label: 'Auto',
    description: cursorAutoModelDescription(shell.cursorCatalogRows),
    available: true,
  },
);
const composerPickerRows = computed(() => {
  const fromCatalog = cursorComposerPickerRowsForActiveModel({
    rows: shell.cursorCatalogRows,
    activeModelId: selectedModelId.value,
  });
  if (fromCatalog.length) {
    return fromCatalog;
  }
  if (!shouldShowCursorManualModelCatalog(selectedModelId.value)) {
    return [];
  }
  return CURSOR_PICKER_COMPOSER_IDS.map((id): CursorCatalogRow => ({
    id,
    label: id,
    description:
      id === CURSOR_PICKER_DEFAULT_MODEL
        ? 'Cursor Composer default — use when API quota models fail'
        : 'Cursor Composer model',
    available: true,
  }));
});
const extraPinnedRows = computed(() =>
  cursorPrimaryModelRows({
    rows: shell.cursorCatalogRows,
    activeModelId: selectedModelId.value,
    visibleExtraModelIds: shell.cursorPickerVisibleModelIds,
  }).filter((row) => !isCursorComposerModel(row.id)),
);
const cursorManageRows = computed(() =>
  cursorManageModelRows({
    rows: shell.cursorCatalogRows,
    searchQuery: modelSearchQuery.value,
  }),
);
const cursorCatalogStatus = computed(() =>
  cursorCatalogStatusLabel({
    loading: shell.cursorCatalogLoadState === 'loading',
    snapshot: shell.cursorRuntimeStatus,
  }),
);
const cursorCatalogCount = computed(() =>
  cursorCatalogCountLabel({
    rows: shell.cursorCatalogRows,
    visibleExtraModelIds: shell.cursorPickerVisibleModelIds,
    searchQuery: modelSearchQuery.value,
  }),
);
const cursorStaleWarning = computed(() =>
  cursorStaleModelWarning({
    modelId: selectedModelId.value,
    rows: shell.cursorCatalogRows,
    snapshot: shell.cursorRuntimeStatus,
  }),
);
const cursorAuthLine = computed(() =>
  composerCursorAuthLine({
    target: currentRuntimeTarget.value,
    cursorSnapshot: shell.cursorRuntimeStatus,
  }),
);
const selectedRuntimeSummary = computed(() => {
  const target = currentRuntimeTarget.value;
  if (!target) {
    return 'No runtime selected';
  }
  const status = target.ready ? 'Ready' : runtimeStatusLine(target);
  return `${target.label} · ${status}`;
});
const autoModelEnabled = computed(() => isCursorAutoModel(selectedModelId.value));
const showAddModelsEntry = computed(
  () => !showAddModelsPanel.value && shouldShowCursorManualModelCatalog(selectedModelId.value),
);
const autoToggleChecked = computed(() => autoModelEnabled.value && !showAddModelsPanel.value);
const showExtraPinnedRows = computed(
  () => extraPinnedRows.value.length > 0 && !showAddModelsPanel.value,
);
const cursorCatalogTotal = computed(() => cursorCatalogModelRows(shell.cursorCatalogRows).length);
const runtimeHint = computed(() => {
  if (shell.runtimeStatusError) {
    return shell.runtimeStatusError;
  }
  if (runtimeNeedsVaultAction(shell.runtimeStatus)) {
    return runtimeVaultHint(shell.runtimeStatus);
  }
  const target = currentRuntimeTarget.value;
  if (target?.ready) {
    return target.auth.message || 'Runtime is ready.';
  }
  if (target?.auth?.message) {
    return target.auth.message;
  }
  return 'Axon-X owns routing and falls back between configured runtimes.';
});
const showVaultAction = computed(() => runtimeNeedsVaultAction(shell.runtimeStatus));
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
const composerAgentBusy = computed(() => shell.composerAgentBusy);
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
const showApprovalBanner = computed(
  () =>
    composerMode.value === 'agent' &&
    shell.agentExecutionAccess === 'full' &&
    shell.ideAgentLinkedRun?.phase === 'awaiting_approval',
);
const executionAccessLabel = computed(() =>
  agentExecutionAccessLabel(shell.agentExecutionAccess),
);
const executionAccessHint = computed(() =>
  agentExecutionAccessHint(shell.agentExecutionAccess),
);
const isFullAccessAgent = computed(
  () => composerMode.value === 'agent' && shell.agentExecutionAccess === 'full',
);
const composerShellClasses = computed(() => ({
  [`agent-dock-composer__shell--${composerMode.value}`]: true,
  'agent-dock-composer__shell--full-access': isFullAccessAgent.value,
  'agent-dock-composer__shell--drag-over': composerDragOver.value,
}));
const modeButtonLabel = computed(() => {
  if (isFullAccessAgent.value) {
    return 'Agent · Full';
  }
  return activeMode.value.label;
});

function closeMenus(): void {
  showContextMenu.value = false;
  showToolsMenu.value = false;
  showModelMenu.value = false;
  showModeMenu.value = false;
  showAddModelsPanel.value = false;
  showRuntimeTargetsPanel.value = false;
  modelSearchQuery.value = '';
}

function toggleSection(section: 'context' | 'tools' | 'model' | 'mode'): void {
  showContextMenu.value = section === 'context' ? !showContextMenu.value : false;
  const openingTools = section === 'tools' ? !showToolsMenu.value : false;
  showToolsMenu.value = openingTools;
  const openingModel = section === 'model' ? !showModelMenu.value : false;
  showModelMenu.value = openingModel;
  showModeMenu.value = section === 'mode' ? !showModeMenu.value : false;
  if (!openingModel) {
    showAddModelsPanel.value = false;
    showRuntimeTargetsPanel.value = false;
    modelSearchQuery.value = '';
  }
  if (openingTools) {
    void shell.loadRuntimeMcpTools();
  }
  if (openingModel) {
    void Promise.all([shell.loadRuntimeStatus(), shell.loadCursorCatalog(true)]);
  }
}

function openAddModelsPanel(): void {
  showAddModelsPanel.value = true;
}

function closeAddModelsPanel(): void {
  showAddModelsPanel.value = false;
  modelSearchQuery.value = '';
}

function selectMode(mode: ComposerMode): void {
  composerMode.value = mode;
  showModeMenu.value = false;
}

function requestFullAccess(): void {
  if (shell.agentExecutionAccess === 'full') {
    return;
  }
  fullAccessConsentChecked.value = false;
  showFullAccessConsent.value = true;
  showModeMenu.value = false;
}

function cancelFullAccessConsent(): void {
  showFullAccessConsent.value = false;
  fullAccessConsentChecked.value = false;
}

function confirmFullAccessConsent(): void {
  if (!fullAccessConsentChecked.value) {
    return;
  }
  shell.setAgentExecutionAccess('full');
  showFullAccessConsent.value = false;
  fullAccessConsentChecked.value = false;
}

function switchToConsultativeAccess(): void {
  shell.setAgentExecutionAccess('consultative');
  showFullAccessConsent.value = false;
  fullAccessConsentChecked.value = false;
}

function handleApproveRun(): void {
  void shell.approveIdeAgentRun();
}

function handleRejectRun(): void {
  void shell.rejectIdeAgentRun();
}

function selectRuntimeTarget(runtimeId: string): void {
  shell.setSelectedRuntimeTarget(runtimeId);
}

function selectComposerModel(modelId: string, options?: { keepMenuOpen?: boolean }): void {
  shell.setSelectedComposerModel(modelId);
  if (!options?.keepMenuOpen) {
    closeMenus();
  }
}

function toggleRuntimeTargetsPanel(): void {
  showRuntimeTargetsPanel.value = !showRuntimeTargetsPanel.value;
}

function onAutoToggleClick(event: MouseEvent): void {
  event.preventDefault();
  event.stopPropagation();
  if (autoModelEnabled.value && !showAddModelsPanel.value) {
    selectComposerModel(CURSOR_PICKER_DEFAULT_MODEL, { keepMenuOpen: true });
    return;
  }
  selectComposerModel('auto', { keepMenuOpen: true });
  closeAddModelsPanel();
}

function selectManageModelRow(modelId: string): void {
  selectComposerModel(modelId);
}

function openVaultSurface(): void {
  navigateToAppSurface('vault');
}

function runtimeStatusLine(record: (typeof runtimeTargets.value)[number]): string {
  if (record.ready) return 'Ready';
  if (!record.available) return 'Not installed';
  return record.auth.message || 'Installed but not ready';
}

function handleStopRun(): void {
  void shell.stopIdeAgentRun();
}

function toggleVoiceCapture(): void {
  if (speechCapture.capturing.value) {
    stopVoiceCapture();
    return;
  }
  shell.interruptKairoVoice();
  startVoiceCapture();
}

async function handleSubmit(event?: Event): Promise<void> {
  event?.preventDefault();
  const draft =
    composerMode.value === 'kairo' ? kairoDraft.value.trim() : shell.ideComposerDraft.trim();
  if (shouldOpenBriefingFromFollowup(draft)) {
    clearBriefingSurfaceOffer();
    kairoConversationReply.value = '';
    shell.focusKairoBriefing();
    if (composerMode.value === 'kairo') {
      kairoDraft.value = '';
    } else {
      shell.ideComposerDraft = '';
    }
    return;
  }
  if (composerMode.value === 'kairo') {
    await submitKairoTurn(draft);
    return;
  }
  const attachmentFiles = composerImages.value.map((image) => image.file);
  await shell.submitIdeComposer(composerMode.value, { attachmentFiles });
  recordComposerHistoryIfSent(draft);
}

async function handleSteer(event?: Event): Promise<void> {
  event?.preventDefault();
  if (composerMode.value === 'kairo') {
    return;
  }
  const draft = shell.ideComposerDraft.trim();
  const attachmentFiles = composerImages.value.map((image) => image.file);
  await shell.steerIdeComposer(composerMode.value, { attachmentFiles });
  recordComposerHistoryIfSent(draft);
}

function removeQueuedMessage(messageId: string): void {
  shell.removeIdeComposerQueuedMessage(messageId);
}

function revealComposerTerminalPanel(): void {
  shell.revealIdeTerminalPanel();
}

function handleResumeRun(): void {
  void shell.resumeIdeAgentRun();
}

function handleComposerKeydown(event: KeyboardEvent): void {
  if (inputRef.value) {
    if (
      shouldRecallPreviousAgentComposerHistory({
        key: event.key,
        shiftKey: event.shiftKey,
        altKey: event.altKey,
        ctrlKey: event.ctrlKey,
        metaKey: event.metaKey,
        selectionStart: inputRef.value.selectionStart,
        selectionEnd: inputRef.value.selectionEnd,
        value: inputRef.value.value,
      }) &&
      composerHistory.value.length > 0
    ) {
      event.preventDefault();
      handleHistory('previous');
      return;
    }

    if (
      shouldRecallNextAgentComposerHistory(
        {
          key: event.key,
          shiftKey: event.shiftKey,
          altKey: event.altKey,
          ctrlKey: event.ctrlKey,
          metaKey: event.metaKey,
          selectionStart: inputRef.value.selectionStart,
          selectionEnd: inputRef.value.selectionEnd,
          value: inputRef.value.value,
        },
        composerHistoryIndex.value >= 0,
      )
    ) {
      event.preventDefault();
      handleHistory('next');
      return;
    }
  }

  if (shouldSteerAgentDockComposer(event)) {
    event.preventDefault();
    void handleSteer();
    return;
  }

  if (!shouldSubmitAgentDockComposer(event)) {
    return;
  }
  event.preventDefault();
  void handleSubmit();
}

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
