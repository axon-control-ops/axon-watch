<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue';

import {
  buildIdeComposerActivityLabel,
  buildIdeStreamActivityLabel,
  FULL_ACCESS_CONSENT_LINES,
} from '../../lib/agent-dock-activity-view';
import {
  agentExecutionAccessHint,
  agentExecutionAccessLabel,
} from '../../lib/agent-execution-access-prefs';
import { navigateToAppSurface } from '../../lib/app-surface-route';
import {
  runtimeNeedsVaultAction,
  runtimeVaultHint,
} from '../../lib/agent-dock-runtime-view';
import {
  composerCursorAuthLine,
} from '../../lib/runtime-auth-view';
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
} from '../../lib/cursor-catalog-view';
import { CURSOR_PICKER_COMPOSER_IDS, CURSOR_PICKER_DEFAULT_MODEL } from '../../lib/cursor-picker-prefs';

import { resizeCommandComposer } from '../../lib/command-composer-autosize';
import {
  type ComposerClipboardImage,
  readClipboardImages,
  readDroppedImages,
  revokeComposerClipboardImages,
  shouldAcceptComposerFileDrop,
  shouldInterceptComposerImagePaste,
} from '../../lib/composer-clipboard-paste';
import { shouldSteerAgentDockComposer, shouldSubmitAgentDockComposer } from '../../lib/agent-dock-composer-input';
import {
  resolveActiveIdeAgentMessage,
} from '../../lib/ide-agent-center-view';
import { summarizeIdeAgentActivity } from '../../lib/ide-agent-activity-view';
import {
  persistAgentComposerHistory,
  readStoredAgentComposerHistory,
  recordAgentComposerHistoryEntry,
  shouldRecallNextAgentComposerHistory,
  shouldRecallPreviousAgentComposerHistory,
  stepAgentComposerHistory,
} from '../../lib/agent-dock-composer-history';
import {
  composerDraftIncludesToken,
  readStoredTerminalSnippet,
  SELECTION_CONTEXT_TOKEN,
  TERMINAL_CONTEXT_TOKEN,
} from '../../lib/ide-composer-context-tokens';
import {
  filterMcpToolsForComposerMode,
  mcpToolDetail,
} from '../../lib/composer-mcp-tools-view';
import {
  kairoConversationError,
  kairoConversationReply,
} from '../../features/kairo-conversation/kairo-conversation-state';
import { useKairoConversation } from '../../features/kairo-conversation/use-kairo-conversation';
import OperatorPersonaMark from '../../components/OperatorPersonaMark.vue';
import PersonaTitle from '../../components/PersonaTitle.vue';
import { OPERATOR_PERSONA_NAME } from '../../lib/operator-persona-name';
import { useShellStore } from '../../stores/shell';

type ComposerMode = 'agent' | 'plan' | 'ask' | 'kairo';

const MODE_OPTIONS: Array<{
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
const contextWorkspace = ref(false);
const contextActiveFile = ref(false);
const contextSelection = ref(false);
const contextTerminal = ref(false);
const contextIde = ref(false);
const contextPinned = ref(false);
const composerHistory = ref<string[]>([]);
const composerHistoryWorkspaceId = ref<string | null>(null);
const composerHistoryIndex = ref(-1);
const composerHistoryScratch = ref('');
const applyingHistoryDraft = ref(false);
const composerImages = ref<ComposerClipboardImage[]>([]);
const composerDragOver = ref(false);

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
const activeFileToken = computed(() =>
  shell.activeWorkspaceFilePath ? `@file:${shell.activeWorkspaceFilePath}` : null,
);
const workspaceToken = computed(() =>
  shell.currentWorkspace?.workspace_id ? `@workspace:${shell.currentWorkspace.workspace_id}` : null,
);
const ideToken = '@ide-context';
const pinnedToken = '@pin-context';
const selectionToken = SELECTION_CONTEXT_TOKEN;
const terminalToken = TERMINAL_CONTEXT_TOKEN;
const hasTerminalSnippet = computed(() =>
  shell.currentWorkspace?.workspace_id
    ? Boolean(readStoredTerminalSnippet(shell.currentWorkspace.workspace_id))
    : false,
);
const selectionChipLabel = computed(() => {
  const selection = shell.editorSelection;
  if (!selection?.text.trim()) {
    return 'Selection';
  }
  if (selection.startLine === selection.endLine) {
    return `L${selection.startLine}`;
  }
  return `L${selection.startLine}-${selection.endLine}`;
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
const attachmentChips = computed(() => {
  const chips: Array<{ key: string; label: string; kind: string }> = [];
  if (contextWorkspace.value && shell.currentWorkspace?.workspace_id) {
    chips.push({
      key: 'workspace',
      kind: 'workspace',
      label: shell.currentWorkspace.workspace_id,
    });
  }
  if (contextActiveFile.value && shell.activeWorkspaceFilePath) {
    chips.push({
      key: 'file',
      kind: 'file',
      label: shell.activeWorkspaceFilePath,
    });
  }
  if (contextSelection.value && shell.hasEditorSelection) {
    chips.push({
      key: 'selection',
      kind: 'selection',
      label: selectionChipLabel.value,
    });
  }
  if (contextTerminal.value && hasTerminalSnippet.value) {
    chips.push({
      key: 'terminal',
      kind: 'terminal',
      label: 'Terminal output',
    });
  }
  if (contextIde.value) {
    chips.push({ key: 'ide', kind: 'ide', label: 'IDE context' });
  }
  if (contextPinned.value) {
    chips.push({ key: 'pin', kind: 'pin', label: 'Pinned' });
  }
  return chips;
});

function resetComposerHistoryNavigation(): void {
  composerHistoryIndex.value = -1;
  composerHistoryScratch.value = '';
}

function loadComposerHistoryForWorkspace(workspaceId: string | null | undefined): void {
  const nextWorkspaceId = workspaceId?.trim() || null;
  if (composerHistoryWorkspaceId.value === nextWorkspaceId) {
    return;
  }
  composerHistoryWorkspaceId.value = nextWorkspaceId;
  composerHistory.value = readStoredAgentComposerHistory(nextWorkspaceId);
  resetComposerHistoryNavigation();
}

function persistCurrentComposerHistory(): void {
  persistAgentComposerHistory(composerHistoryWorkspaceId.value, composerHistory.value);
}

function syncComposerHeight(): void {
  if (!inputRef.value) return;
  resizeCommandComposer(inputRef.value, { compact: true });
}

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

function normalizeDraft(text: string): string {
  return text
    .replace(/[ \t]+\n/g, '\n')
    .replace(/\n{3,}/g, '\n\n')
    .trim();
}

function setTokenEnabled(token: string | null, enabled: boolean): void {
  if (!token) return;
  const escaped = token.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  const pattern = new RegExp(`(^|\\s)${escaped}(?=\\s|$)`, 'g');
  let draft = shell.ideComposerDraft;
  draft = draft.replace(pattern, ' ').replace(/[ ]{2,}/g, ' ');
  draft = normalizeDraft(draft);
  if (enabled) {
    draft = draft ? `${token}\n${draft}` : token;
  }
  shell.ideComposerDraft = draft;
}

function toggleContext(kind: 'workspace' | 'file' | 'selection' | 'terminal' | 'ide' | 'pin'): void {
  if (kind === 'workspace') {
    contextWorkspace.value = !contextWorkspace.value;
    setTokenEnabled(workspaceToken.value, contextWorkspace.value);
    return;
  }
  if (kind === 'file') {
    contextActiveFile.value = !contextActiveFile.value;
    setTokenEnabled(activeFileToken.value, contextActiveFile.value);
    return;
  }
  if (kind === 'selection') {
    contextSelection.value = !contextSelection.value;
    setTokenEnabled(selectionToken, contextSelection.value);
    return;
  }
  if (kind === 'terminal') {
    contextTerminal.value = !contextTerminal.value;
    setTokenEnabled(terminalToken, contextTerminal.value);
    return;
  }
  if (kind === 'ide') {
    contextIde.value = !contextIde.value;
    setTokenEnabled(ideToken, contextIde.value);
    return;
  }
  contextPinned.value = !contextPinned.value;
  setTokenEnabled(pinnedToken, contextPinned.value);
}

function removeChip(key: string): void {
  if (key === 'workspace') {
    contextWorkspace.value = false;
    setTokenEnabled(workspaceToken.value, false);
    return;
  }
  if (key === 'file') {
    contextActiveFile.value = false;
    setTokenEnabled(activeFileToken.value, false);
    return;
  }
  if (key === 'selection') {
    contextSelection.value = false;
    setTokenEnabled(selectionToken, false);
    return;
  }
  if (key === 'terminal') {
    contextTerminal.value = false;
    setTokenEnabled(terminalToken, false);
    return;
  }
  if (key === 'ide') {
    contextIde.value = false;
    setTokenEnabled(ideToken, false);
    return;
  }
  contextPinned.value = false;
  setTokenEnabled(pinnedToken, false);
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

function applyHistoryDraft(draft: string): void {
  applyingHistoryDraft.value = true;
  shell.restoreComposerDraft(draft);
  void nextTick(() => {
    syncComposerHeight();
    if (!inputRef.value) {
      return;
    }
    const caret = inputRef.value.value.length;
    inputRef.value.setSelectionRange(caret, caret);
  });
}

function handleHistory(direction: 'previous' | 'next'): void {
  const step = stepAgentComposerHistory({
    entries: composerHistory.value,
    index: composerHistoryIndex.value,
    scratch: composerHistoryScratch.value,
    currentDraft: shell.ideComposerDraft,
    direction,
  });
  composerHistoryIndex.value = step.index;
  composerHistoryScratch.value = step.scratch;
  applyHistoryDraft(step.draft);
}

async function handleSubmit(event?: Event): Promise<void> {
  event?.preventDefault();
  if (composerMode.value === 'kairo') {
    const draft = kairoDraft.value.trim();
    await submitKairoTurn(draft);
    return;
  }
  const draft = shell.ideComposerDraft.trim();
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

function recordComposerHistoryIfSent(draft: string): void {
  if (composerImages.value.length) {
    revokeComposerClipboardImages(composerImages.value);
    composerImages.value = [];
  }
  if (draft && !shell.ideComposerDraft.trim() && shell.commandMutationState === 'idle') {
    composerHistory.value = recordAgentComposerHistoryEntry(composerHistory.value, draft);
    persistCurrentComposerHistory();
    resetComposerHistoryNavigation();
  }
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

function addComposerImages(images: ComposerClipboardImage[]): void {
  if (!images.length) {
    return;
  }
  composerImages.value = [...composerImages.value, ...images];
}

function handleComposerPaste(event: ClipboardEvent): void {
  const images = readClipboardImages(event);
  if (!shouldInterceptComposerImagePaste(images)) {
    return;
  }

  event.preventDefault();
  addComposerImages(images);
}

function handleComposerDragOver(event: DragEvent): void {
  if (!shouldAcceptComposerFileDrop(event)) {
    return;
  }
  event.preventDefault();
  if (event.dataTransfer) {
    event.dataTransfer.dropEffect = 'copy';
  }
  composerDragOver.value = true;
}

function handleComposerDragLeave(event: DragEvent): void {
  const nextTarget = event.relatedTarget as Node | null;
  if (nextTarget && event.currentTarget instanceof Node && event.currentTarget.contains(nextTarget)) {
    return;
  }
  composerDragOver.value = false;
}

function handleComposerDrop(event: DragEvent): void {
  event.preventDefault();
  composerDragOver.value = false;
  const images = readDroppedImages(event);
  if (!shouldInterceptComposerImagePaste(images)) {
    return;
  }
  addComposerImages(images);
}

function removeComposerImage(imageId: string): void {
  const removed = composerImages.value.find((image) => image.id === imageId);
  if (removed) {
    URL.revokeObjectURL(removed.previewUrl);
  }
  composerImages.value = composerImages.value.filter((image) => image.id !== imageId);
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

function syncContextFromDraft(): void {
  const draft = shell.ideComposerDraft;
  if (workspaceToken.value) {
    contextWorkspace.value = composerDraftIncludesToken(draft, workspaceToken.value);
  }
  if (activeFileToken.value) {
    contextActiveFile.value = composerDraftIncludesToken(draft, activeFileToken.value);
  }
  contextSelection.value = composerDraftIncludesToken(draft, selectionToken);
  contextTerminal.value = composerDraftIncludesToken(draft, terminalToken);
  contextIde.value = composerDraftIncludesToken(draft, ideToken);
  contextPinned.value = composerDraftIncludesToken(draft, pinnedToken);
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
  revokeComposerClipboardImages(composerImages.value);
});
</script>

<template>
  <Teleport to="body">
    <div
      v-if="showFullAccessConsent"
      class="agent-dock-full-access-consent"
      role="dialog"
      aria-modal="true"
      aria-labelledby="full-access-consent-title"
      @click.self="cancelFullAccessConsent"
    >
      <div class="agent-dock-full-access-consent__card">
        <p id="full-access-consent-title" class="agent-dock-full-access-consent__title">
          Enable Full Access?
        </p>
        <ul class="agent-dock-full-access-consent__list">
          <li v-for="line in FULL_ACCESS_CONSENT_LINES" :key="line">{{ line }}</li>
        </ul>
        <label class="agent-dock-full-access-consent__check">
          <input v-model="fullAccessConsentChecked" type="checkbox">
          <span>I understand and consent to Full Access for Agent turns in this workspace.</span>
        </label>
        <div class="agent-dock-full-access-consent__actions">
          <button
            type="button"
            class="agent-dock-full-access-consent__btn agent-dock-full-access-consent__btn--cancel"
            @click="cancelFullAccessConsent"
          >
            Cancel
          </button>
          <button
            type="button"
            class="agent-dock-full-access-consent__btn agent-dock-full-access-consent__btn--confirm"
            :disabled="!fullAccessConsentChecked"
            @click="confirmFullAccessConsent"
          >
            Enable Full Access
          </button>
        </div>
      </div>
    </div>
  </Teleport>

  <form
    class="agent-dock-composer"
    @submit="handleSubmit"
    @dragover="handleComposerDragOver"
    @dragleave="handleComposerDragLeave"
    @drop="handleComposerDrop"
  >
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
        <div
          v-if="attachmentChips.length"
          class="agent-dock-composer__chips"
          aria-label="Composer context"
        >
          <button
            v-for="chip in attachmentChips"
            :key="chip.key"
            type="button"
            class="agent-dock-composer__chip"
            :title="chip.label"
            @click="removeChip(chip.key)"
          >
            <span class="agent-dock-composer__chip-kind">{{ chip.kind }}</span>
            <span class="agent-dock-composer__chip-label">{{ chip.label }}</span>
            <span class="agent-dock-composer__chip-remove" aria-hidden="true">×</span>
          </button>
        </div>

        <div
          v-if="composerImages.length"
          class="agent-dock-composer__image-strip"
          aria-label="Attached images"
        >
          <button
            v-for="image in composerImages"
            :key="image.id"
            type="button"
            class="agent-dock-composer__image-card"
            :title="`Remove ${image.name}`"
            @click="removeComposerImage(image.id)"
          >
            <img
              class="agent-dock-composer__image-preview"
              :src="image.previewUrl"
              :alt="image.name"
            >
            <span class="agent-dock-composer__image-remove" aria-hidden="true">×</span>
          </button>
        </div>

        <div
          v-if="shell.ideComposerQueue.length"
          class="agent-dock-composer__queue"
          role="status"
          aria-live="polite"
        >
          <p class="agent-dock-composer__queue-summary">
            {{ shell.ideComposerQueueSummary }}
          </p>
          <ul class="agent-dock-composer__queue-list">
            <li
              v-for="item in shell.ideComposerQueue"
              :key="item.id"
              class="agent-dock-composer__queue-item"
            >
              <span class="agent-dock-composer__queue-text">{{ item.content }}</span>
              <button
                type="button"
                class="agent-dock-composer__queue-remove"
                aria-label="Remove queued message"
                @click="removeQueuedMessage(item.id)"
              >
                ×
              </button>
            </li>
          </ul>
        </div>

        <div class="agent-dock-composer__input-row">
          <textarea
            id="agent-dock-composer-input"
            ref="inputRef"
            v-model="composerDraftModel"
            class="agent-dock-composer__input"
            rows="1"
            :aria-label="composerMode === 'kairo' ? `${OPERATOR_PERSONA_NAME} composer` : 'Agent composer'"
            :placeholder="composerPlaceholder"
            :disabled="!shell.currentWorkspace"
            @input="syncComposerHeight"
            @keydown="handleComposerKeydown"
            @paste="handleComposerPaste"
          />
        </div>

        <div class="agent-dock-composer__footer">
          <div
            v-if="composerActivityChips.length"
            class="agent-dock-composer__activity-chips"
            aria-label="Live agent activity"
          >
            <button
              v-for="chip in composerActivityChips"
              :key="chip.id"
              type="button"
              class="agent-dock-composer__activity-chip"
              :class="`agent-dock-composer__activity-chip--${chip.kind}`"
              :disabled="chip.kind !== 'terminal'"
              @click="chip.kind === 'terminal' ? revealComposerTerminalPanel() : undefined"
            >
              {{ chip.label }}
            </button>
          </div>

          <div class="agent-dock-composer__tools" @click.stop>
            <div class="agent-dock-composer__tool-group">
              <button
                type="button"
                class="agent-dock-composer__tool"
                :class="{ 'is-active': showContextMenu || attachmentChips.length > 0 }"
                title="Open context and quick run controls"
                aria-label="Open context menu"
                @click="toggleSection('context')"
              >
                <span class="agent-dock-composer__tool-plus" aria-hidden="true">+</span>
                <span>Context</span>
                <span
                  v-if="attachmentChips.length"
                  class="agent-dock-composer__tool-count"
                >
                  {{ attachmentChips.length }}
                </span>
              </button>
              <div
                v-if="showContextMenu"
                class="agent-dock-composer__menu agent-dock-composer__menu--context"
              >
                <button
                  type="button"
                  class="agent-dock-composer__menu-item"
                  :class="{ 'is-active': contextWorkspace }"
                  @click="toggleContext('workspace')"
                >
                  <span>Workspace</span>
                  <small>{{ shell.currentWorkspace?.workspace_id ?? 'Unavailable' }}</small>
                </button>
                <button
                  type="button"
                  class="agent-dock-composer__menu-item"
                  :class="{ 'is-active': contextActiveFile }"
                  :disabled="!shell.activeWorkspaceFilePath"
                  @click="toggleContext('file')"
                >
                  <span>Active file</span>
                  <small>{{ shell.activeWorkspaceFilePath ?? 'Open a file first' }}</small>
                </button>
                <button
                  type="button"
                  class="agent-dock-composer__menu-item"
                  :class="{ 'is-active': contextSelection }"
                  :disabled="!shell.hasEditorSelection"
                  @click="toggleContext('selection')"
                >
                  <span>Selection</span>
                  <small>{{ shell.hasEditorSelection ? selectionChipLabel : 'Highlight code in the editor' }}</small>
                </button>
                <button
                  type="button"
                  class="agent-dock-composer__menu-item"
                  :class="{ 'is-active': contextTerminal }"
                  :disabled="!hasTerminalSnippet"
                  @click="toggleContext('terminal')"
                >
                  <span>Terminal</span>
                  <small>{{ hasTerminalSnippet ? 'Recent terminal output' : 'Run a command first' }}</small>
                </button>
                <button
                  type="button"
                  class="agent-dock-composer__menu-item"
                  :class="{ 'is-active': contextIde }"
                  @click="toggleContext('ide')"
                >
                  <span>IDE context</span>
                  <small>Open file and editor state</small>
                </button>
                <button
                  type="button"
                  class="agent-dock-composer__menu-item"
                  :class="{ 'is-active': contextPinned }"
                  @click="toggleContext('pin')"
                >
                  <span>Pin context</span>
                  <small>Keep current context across turns</small>
                </button>
              </div>
            </div>

            <div class="agent-dock-composer__tool-group">
              <button
                type="button"
                class="agent-dock-composer__tool"
                :class="{ 'is-active': showToolsMenu }"
                title="Runtime MCP tools available for this mode"
                aria-label="Open tools registry"
                @click="toggleSection('tools')"
              >
                <span>Tools</span>
                <span
                  v-if="mcpToolsForMode.length"
                  class="agent-dock-composer__tool-count"
                >
                  {{ mcpToolsForMode.length }}
                </span>
              </button>
              <div
                v-if="showToolsMenu"
                class="agent-dock-composer__menu agent-dock-composer__menu--tools"
              >
                <p class="agent-dock-composer__menu-heading">Runtime tools · {{ composerMode }}</p>
                <p
                  v-if="shell.runtimeMcpToolsLoadState === 'loading'"
                  class="agent-dock-composer__menu-note"
                >
                  Loading tool registry…
                </p>
                <p
                  v-else-if="!mcpToolsForMode.length"
                  class="agent-dock-composer__menu-note"
                >
                  No tools registered for this mode.
                </p>
                <button
                  v-for="tool in mcpToolsForMode"
                  :key="tool.id"
                  type="button"
                  class="agent-dock-composer__menu-item agent-dock-composer__menu-item--readonly"
                  disabled
                >
                  <span>{{ tool.label }}</span>
                  <small>{{ mcpToolDetail(tool) }}</small>
                </button>
              </div>
            </div>

            <div class="agent-dock-composer__tool-group">
              <button
                type="button"
                class="agent-dock-composer__tool agent-dock-composer__tool--model"
                :class="{ 'is-active': showModelMenu }"
                :title="`Current runtime: ${runtimeDetail}`"
                :aria-label="`Open model picker: ${runtimeLabel}`"
                :aria-expanded="showModelMenu"
                @click="toggleSection('model')"
              >
                <span class="agent-dock-composer__tool-icon" aria-hidden="true">⚡</span>
                <span class="agent-dock-composer__tool-label">{{ runtimeLabel }}</span>
                <span class="agent-dock-composer__tool-chevron" aria-hidden="true">▾</span>
              </button>
              <div v-if="showModelMenu" class="agent-dock-composer__menu agent-dock-composer__menu--runtime">
                <button
                  type="button"
                  class="agent-dock-composer__menu-section-toggle"
                  :aria-expanded="showRuntimeTargetsPanel"
                  @click.stop="toggleRuntimeTargetsPanel"
                >
                  <span class="agent-dock-composer__menu-section-label">Runtime target</span>
                  <span class="agent-dock-composer__menu-section-value">{{ selectedRuntimeSummary }}</span>
                  <span class="agent-dock-composer__menu-section-chevron" aria-hidden="true">
                    {{ showRuntimeTargetsPanel ? '▴' : '▾' }}
                  </span>
                </button>
                <div v-if="showRuntimeTargetsPanel" class="agent-dock-composer__menu-section-body">
                  <button
                    v-for="record in runtimeTargets"
                    :key="record.id"
                    type="button"
                    class="agent-dock-composer__menu-item agent-dock-composer__menu-item--compact"
                    :class="{ 'agent-dock-composer__menu-item--selected': record.id === shell.selectedRuntimeTargetId }"
                    @click="selectRuntimeTarget(record.id)"
                  >
                    <span>{{ record.label }}</span>
                    <small>{{ runtimeStatusLine(record) }}</small>
                  </button>
                </div>

                <template v-if="showCursorCatalog">
                  <p class="agent-dock-composer__menu-caption">Model catalog</p>
                  <p class="agent-dock-composer__menu-note agent-dock-composer__menu-note--status">
                    {{ cursorCatalogStatus }}
                  </p>
                  <p v-if="cursorAuthLine" class="agent-dock-composer__menu-note agent-dock-composer__menu-note--auth">
                    {{ cursorAuthLine }}
                  </p>
                  <p v-if="shell.cursorCatalogLoadState === 'loading'" class="agent-dock-composer__menu-note">
                    Loading Cursor models…
                  </p>
                  <p v-else-if="shell.cursorCatalogError" class="agent-dock-composer__menu-note">
                    {{ shell.cursorCatalogError }}
                  </p>

                  <template v-if="!showAddModelsPanel">
                    <label class="agent-dock-composer__auto-toggle" @click.stop>
                      <span>
                        <strong>Auto</strong>
                        <small>{{ autoModelRow.description }}</small>
                      </span>
                      <input
                        type="checkbox"
                        role="switch"
                        :checked="autoToggleChecked"
                        @click="onAutoToggleClick"
                      >
                    </label>

                    <button
                      v-for="row in composerPickerRows"
                      :key="row.id"
                      type="button"
                      class="agent-dock-composer__menu-item"
                      :class="{ 'agent-dock-composer__menu-item--selected': row.id === selectedModelId }"
                      :disabled="!row.available"
                      @click="selectComposerModel(row.id)"
                    >
                      <span class="agent-dock-composer__model-label">
                        {{ row.label }}
                        <span v-if="row.badge" class="agent-dock-composer__model-badge">{{ row.badge }}</span>
                      </span>
                      <small>{{ row.description }}</small>
                    </button>

                    <template v-if="showExtraPinnedRows">
                      <p class="agent-dock-composer__menu-caption">Pinned models</p>
                      <button
                        v-for="row in extraPinnedRows"
                        :key="row.id"
                        type="button"
                        class="agent-dock-composer__menu-item"
                        :class="{ 'agent-dock-composer__menu-item--selected': row.id === selectedModelId }"
                        :disabled="!row.available"
                        @click="selectComposerModel(row.id)"
                      >
                        <span class="agent-dock-composer__model-label">
                          {{ row.label }}
                          <span v-if="row.badge" class="agent-dock-composer__model-badge">{{ row.badge }}</span>
                        </span>
                        <small>{{ row.description }}</small>
                      </button>
                    </template>

                    <button
                      v-if="showAddModelsEntry"
                      type="button"
                      class="agent-dock-composer__menu-item agent-dock-composer__menu-item--add-models"
                      @click.stop="openAddModelsPanel"
                    >
                      <span>Add models</span>
                      <small>Browse {{ cursorCatalogTotal }} catalog models</small>
                    </button>

                    <p v-if="cursorStaleWarning" class="agent-dock-composer__menu-note agent-dock-composer__menu-note--warning">
                      {{ cursorStaleWarning }}
                    </p>
                    <p v-if="shell.cursorRuntimeStatus?.catalog_source === 'fallback'" class="agent-dock-composer__menu-note">
                      Live catalog unavailable — showing curated fallback models.
                    </p>
                  </template>

                  <template v-else>
                    <div class="agent-dock-composer__model-search-row">
                      <button
                        type="button"
                        class="agent-dock-composer__menu-back"
                        @click.stop="closeAddModelsPanel"
                      >
                        ← Back
                      </button>
                      <input
                        v-model="modelSearchQuery"
                        type="search"
                        class="agent-dock-composer__model-search"
                        placeholder="Search models"
                        @click.stop
                      >
                    </div>
                    <p class="agent-dock-composer__menu-note">{{ cursorCatalogCount }}</p>
                    <button
                      v-for="row in cursorManageRows"
                      :key="row.id"
                      type="button"
                      class="agent-dock-composer__menu-item agent-dock-composer__menu-item--compact"
                      :class="{ 'agent-dock-composer__menu-item--selected': row.id === selectedModelId }"
                      :disabled="!row.available"
                      @click="selectManageModelRow(row.id)"
                    >
                      <span class="agent-dock-composer__model-label">
                        {{ row.label }}
                        <span v-if="row.badge" class="agent-dock-composer__model-badge">{{ row.badge }}</span>
                      </span>
                      <small>{{ row.description }}</small>
                    </button>
                    <p
                      v-if="!cursorManageRows.length"
                      class="agent-dock-composer__menu-note"
                    >
                      No models match your search.
                    </p>
                  </template>
                </template>
                <p v-else class="agent-dock-composer__menu-note">
                  Selected model: {{ selectedModelLabel }}
                </p>

                <p v-if="!showAddModelsPanel && runtimeHint && !cursorAuthLine" class="agent-dock-composer__menu-note">
                  {{ runtimeHint }}
                </p>
                <p
                  v-else-if="!showAddModelsPanel && runtimeHint && showVaultAction"
                  class="agent-dock-composer__menu-note"
                >
                  {{ runtimeHint }}
                </p>
                <button
                  v-if="showVaultAction"
                  type="button"
                  class="agent-dock-composer__vault-action"
                  @click="openVaultSurface"
                >
                  Open Vault
                </button>
              </div>
            </div>

            <div class="agent-dock-composer__tool-group">
              <button
                type="button"
                class="agent-dock-composer__tool agent-dock-composer__tool--mode"
                :class="{
                  'is-active': showModeMenu,
                  'agent-dock-composer__tool--mode-full-access': isFullAccessAgent,
                }"
                :data-mode="composerMode"
                :title="isFullAccessAgent ? executionAccessHint : activeMode.hint"
                :aria-label="`Conversation mode: ${modeButtonLabel}`"
                @click="toggleSection('mode')"
              >
                <span class="agent-dock-composer__tool-icon" aria-hidden="true">{{ activeMode.icon }}</span>
                <span class="agent-dock-composer__tool-label agent-dock-composer__mode-chip">
                  <PersonaTitle v-if="composerMode === 'kairo'" mark-size="xs" />
                  <template v-else>{{ modeButtonLabel }}</template>
                </span>
                <span class="agent-dock-composer__tool-chevron" aria-hidden="true">▾</span>
              </button>
              <div v-if="showModeMenu" class="agent-dock-composer__menu">
                <p class="agent-dock-composer__menu-caption">Conversation mode</p>
                <button
                  v-for="option in MODE_OPTIONS"
                  :key="option.key"
                  type="button"
                  class="agent-dock-composer__menu-item"
                  :class="{ 'is-active': composerMode === option.key }"
                  @click="selectMode(option.key)"
                >
                  <span class="agent-dock-composer__menu-item-label">
                    <PersonaTitle v-if="option.key === 'kairo'" mark-size="xs" />
                    <template v-else>{{ option.icon }} {{ option.label }}</template>
                  </span>
                  <small>{{ option.hint }}</small>
                </button>
                <template v-if="composerMode === 'agent'">
                  <p class="agent-dock-composer__menu-caption">Execution access</p>
                  <button
                    type="button"
                    class="agent-dock-composer__menu-item"
                    :class="{ 'is-active': shell.agentExecutionAccess === 'consultative' }"
                    @click="switchToConsultativeAccess"
                  >
                    <span>◌ Consultative</span>
                    <small>{{ agentExecutionAccessHint('consultative') }}</small>
                  </button>
                  <button
                    type="button"
                    class="agent-dock-composer__menu-item agent-dock-composer__menu-item--full-access"
                    :class="{ 'is-active': shell.agentExecutionAccess === 'full' }"
                    @click="requestFullAccess"
                  >
                    <span>⬡ Full Access</span>
                    <small>{{ agentExecutionAccessHint('full') }}</small>
                  </button>
                </template>
              </div>
            </div>
          </div>

          <div class="agent-dock-composer__actions">
            <p
              v-if="composerQueueHint"
              class="agent-dock-composer__queue-hint"
            >
              {{ composerQueueHint }}
            </p>
            <button
              v-if="showComposerResume"
              type="button"
              class="agent-dock-composer__resume"
              :disabled="shell.runMutationState === 'resuming'"
              @click="handleResumeRun"
            >
              {{ shell.runMutationState === 'resuming' ? 'Resuming…' : 'Resume' }}
            </button>
            <button
              v-if="composerMode === 'kairo' && speechCapture.supported"
              type="button"
              class="agent-dock-composer__tool agent-dock-composer__tool--mic"
              :class="{ 'is-active': speechCapture.capturing.value }"
              :disabled="shell.operatorPresenceSettings.privacy_mode || kairoPending"
              @click="toggleVoiceCapture"
            >
              {{ speechCapture.capturing.value ? 'Listening…' : 'Mic' }}
            </button>
            <button
              v-if="showComposerStop"
              type="button"
              class="agent-dock-composer__send agent-dock-composer__send--stop"
              :disabled="shell.runMutationState === 'stopping'"
              :aria-label="shell.runMutationState === 'stopping' ? 'Stopping run' : 'Stop run'"
              @click="handleStopRun"
            >
              <span
                v-if="shell.runMutationState === 'stopping'"
                class="agent-dock-composer__send-spinner"
                aria-hidden="true"
              />
              <span v-else class="agent-dock-composer__stop-icon" aria-hidden="true" />
            </button>
            <button
              v-else
              type="submit"
              class="agent-dock-composer__send"
              :disabled="!canSubmitComposer"
              :aria-label="composerSubmitLabel"
            >
              <span
                v-if="shell.commandMutationState === 'submitting' || (composerMode === 'kairo' && kairoPending)"
                class="agent-dock-composer__send-spinner"
                aria-hidden="true"
              />
              <span v-else class="agent-dock-composer__send-icon" aria-hidden="true">
                {{ composerMode === 'kairo' ? 'Ask' : '↑' }}
              </span>
            </button>
          </div>
        </div>
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
