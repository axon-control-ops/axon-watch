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
  cursorManageModelRows,
  cursorModelLabel,
  cursorPrimaryModelRows,
  cursorStaleModelWarning,
  isCursorAutoModel,
} from '../../lib/cursor-catalog-view';

import { resizeCommandComposer } from '../../lib/command-composer-autosize';
import { shouldSubmitAgentDockComposer } from '../../lib/agent-dock-composer-input';
import { useShellStore } from '../../stores/shell';

type ComposerMode = 'agent' | 'plan' | 'ask';

const MODE_OPTIONS: Array<{
  key: ComposerMode;
  label: string;
  icon: string;
  hint: string;
}> = [
  { key: 'ask', label: 'Ask', icon: '◯', hint: 'Read-only answers, no tool execution' },
  { key: 'plan', label: 'Plan', icon: '◈', hint: 'Map steps before executing' },
  { key: 'agent', label: 'Agent', icon: '◎', hint: 'Agent loop with tools and approvals' },
];

const shell = useShellStore();
const inputRef = ref<HTMLTextAreaElement | null>(null);
const composerMode = ref<ComposerMode>(
  (shell.runtimeSummary?.runtime_identity.mode_default as ComposerMode) || 'agent',
);
const showContextMenu = ref(false);
const showModelMenu = ref(false);
const showModeMenu = ref(false);
const showFullAccessConsent = ref(false);
const fullAccessConsentChecked = ref(false);
const showAddModelsPanel = ref(false);
const showRuntimeTargetsPanel = ref(false);
const modelSearchQuery = ref('');
const contextWorkspace = ref(false);
const contextActiveFile = ref(false);
const contextIde = ref(false);
const contextPinned = ref(false);

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
const cursorPrimaryRows = computed(() =>
  cursorPrimaryModelRows({
    rows: shell.cursorCatalogRows,
    activeModelId: selectedModelId.value,
    visibleExtraModelIds: shell.cursorPickerVisibleModelIds,
  }),
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
  () => !autoModelEnabled.value && !showAddModelsPanel.value,
);
const autoToggleChecked = computed(
  () => autoModelEnabled.value && !showAddModelsPanel.value,
);
const showCursorPrimaryRows = computed(() => !isCursorAutoModel(selectedModelId.value));
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
const showComposerStop = computed(() => {
  const run = shell.ideAgentLinkedRun ?? shell.primaryActiveRun;
  if (!run) return false;
  return shell.canStopPrimaryRun || run.phase === 'executing';
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
  if (contextIde.value) {
    chips.push({ key: 'ide', kind: 'ide', label: 'IDE context' });
  }
  if (contextPinned.value) {
    chips.push({ key: 'pin', kind: 'pin', label: 'Pinned' });
  }
  return chips;
});

function syncComposerHeight(): void {
  if (!inputRef.value) return;
  resizeCommandComposer(inputRef.value, { compact: true });
}

function closeMenus(): void {
  showContextMenu.value = false;
  showModelMenu.value = false;
  showModeMenu.value = false;
  showAddModelsPanel.value = false;
  showRuntimeTargetsPanel.value = false;
  modelSearchQuery.value = '';
}

function toggleSection(section: 'context' | 'model' | 'mode'): void {
  showContextMenu.value = section === 'context' ? !showContextMenu.value : false;
  const openingModel = section === 'model' ? !showModelMenu.value : false;
  showModelMenu.value = openingModel;
  showModeMenu.value = section === 'mode' ? !showModeMenu.value : false;
  if (!openingModel) {
    showAddModelsPanel.value = false;
    showRuntimeTargetsPanel.value = false;
    modelSearchQuery.value = '';
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
  let draft = shell.operatorCommandDraft;
  draft = draft.replace(pattern, ' ').replace(/[ ]{2,}/g, ' ');
  draft = normalizeDraft(draft);
  if (enabled) {
    draft = draft ? `${token}\n${draft}` : token;
  }
  shell.operatorCommandDraft = draft;
}

function toggleContext(kind: 'workspace' | 'file' | 'ide' | 'pin'): void {
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

function selectComposerModel(modelId: string): void {
  shell.setSelectedComposerModel(modelId);
  closeMenus();
}

function toggleRuntimeTargetsPanel(): void {
  showRuntimeTargetsPanel.value = !showRuntimeTargetsPanel.value;
}

function onAutoToggleClick(event: MouseEvent): void {
  event.preventDefault();
  if (autoModelEnabled.value && !showAddModelsPanel.value) {
    openAddModelsPanel();
    return;
  }
  selectComposerModel('auto');
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
  void shell.stopPrimaryRun();
}

function handleSubmit(event?: Event): void {
  event?.preventDefault();
  void shell.submitIdeComposer(composerMode.value);
}

function handleComposerKeydown(event: KeyboardEvent): void {
  if (!shouldSubmitAgentDockComposer(event)) {
    return;
  }
  event.preventDefault();
  handleSubmit();
}

function handleDocumentClick(): void {
  closeMenus();
}

watch(
  () => shell.operatorCommandDraft,
  () => {
    void nextTick(syncComposerHeight);
  },
);

onMounted(() => {
  syncComposerHeight();
  document.addEventListener('click', handleDocumentClick);
});

onUnmounted(() => {
  document.removeEventListener('click', handleDocumentClick);
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

  <form class="agent-dock-composer" @submit="handleSubmit">
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
          v-if="shell.ideComposerActivity || shell.agentStreamActive"
          class="agent-dock-composer__activity"
          :class="{
            'agent-dock-composer__activity--full-access': isFullAccessAgent,
          }"
          role="status"
          aria-live="polite"
        >
          <span class="agent-dock-composer__activity-dot" aria-hidden="true" />
          <span>{{ shell.ideComposerActivity?.label ?? 'Agent is working…' }}</span>
        </div>

        <div class="agent-dock-composer__input-row">
          <textarea
            id="agent-dock-composer-input"
            ref="inputRef"
            v-model="shell.operatorCommandDraft"
            class="agent-dock-composer__input"
            rows="1"
            aria-label="Agent composer"
            :placeholder="composerPlaceholder"
            :disabled="!shell.currentWorkspace"
            @input="syncComposerHeight"
            @keydown="handleComposerKeydown"
          />
        </div>

        <div class="agent-dock-composer__footer">
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
                class="agent-dock-composer__tool agent-dock-composer__tool--model"
                :class="{ 'is-active': showModelMenu }"
                :title="`Current runtime: ${runtimeDetail}`"
                :aria-label="`Open model picker: ${runtimeLabel}`"
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
                      v-for="row in cursorPrimaryRows"
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

                    <button
                      v-if="showAddModelsEntry && showCursorPrimaryRows && cursorCatalogTotal > cursorPrimaryRows.length"
                      type="button"
                      class="agent-dock-composer__menu-item agent-dock-composer__menu-item--add-models"
                      @click.stop="openAddModelsPanel"
                    >
                      <span>Add models</span>
                      <small>Browse {{ cursorCatalogTotal }} catalog models</small>
                    </button>
                    <button
                      v-else-if="showAddModelsEntry && !showCursorPrimaryRows"
                      type="button"
                      class="agent-dock-composer__menu-item agent-dock-composer__menu-item--add-models"
                      @click.stop="openAddModelsPanel"
                    >
                      <span>Add models</span>
                      <small>Pin a specific Cursor model</small>
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
                <span class="agent-dock-composer__tool-label">{{ modeButtonLabel }}</span>
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
                  <span>{{ option.icon }} {{ option.label }}</span>
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
              :disabled="!shell.canSubmitOperatorCommand"
              :aria-label="shell.commandMutationState === 'submitting' ? 'Sending command' : 'Send command'"
            >
              <span
                v-if="shell.commandMutationState === 'submitting'"
                class="agent-dock-composer__send-spinner"
                aria-hidden="true"
              />
              <span v-else class="agent-dock-composer__send-icon" aria-hidden="true">↑</span>
            </button>
          </div>
        </div>
      </div>
    </div>

    <p v-if="!shell.currentWorkspace" class="agent-dock-composer__empty">
      Select a workspace to send commands.
    </p>
    <p v-if="shell.commandMutationError" class="agent-dock-composer__error">
      {{ shell.commandMutationError }}
    </p>
  </form>
</template>
