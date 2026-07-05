<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue';

import { resizeCommandComposer } from '../../lib/command-composer-autosize';
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
const contextWorkspace = ref(false);
const contextActiveFile = ref(false);
const contextIde = ref(false);
const contextPinned = ref(false);

const activeMode = computed(
  () => MODE_OPTIONS.find((option) => option.key === composerMode.value) ?? MODE_OPTIONS[2],
);
const runtimeLabel = computed(() => {
  const identity = shell.runtimeSummary?.runtime_identity;
  if (!identity) return 'Model';
  return identity.model_name;
});
const runtimeDetail = computed(() => {
  const identity = shell.runtimeSummary?.runtime_identity;
  if (!identity) return 'Control-plane runtime';
  return `${identity.provider_name} · ${identity.model_name}`;
});
const runtimeHint = computed(() => {
  const identity = shell.runtimeSummary?.runtime_identity;
  if (!identity) return 'Locked to control-plane runtime';
  const parts = [
    identity.tool_calling_supported ? 'tools' : null,
    identity.reasoning_supported ? 'reasoning' : null,
  ]
    .filter(Boolean)
    .join(' · ');
  return parts ? `Locked to control-plane · ${parts}` : 'Locked to control-plane';
});
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
  const run = shell.primaryActiveRun;
  if (!run) return false;
  return shell.canStopPrimaryRun || run.phase === 'executing';
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
}

function toggleSection(section: 'context' | 'model' | 'mode'): void {
  showContextMenu.value = section === 'context' ? !showContextMenu.value : false;
  showModelMenu.value = section === 'model' ? !showModelMenu.value : false;
  showModeMenu.value = section === 'mode' ? !showModeMenu.value : false;
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

function handleStopRun(): void {
  void shell.stopPrimaryRun();
}

function handleSubmit(event?: Event): void {
  event?.preventDefault();
  shell.submitOperatorCommand();
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
  <form class="agent-dock-composer" @submit="handleSubmit">
    <div
      class="agent-dock-composer__shell"
      :class="`agent-dock-composer__shell--${composerMode}`"
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
            @keydown.meta.enter.prevent="handleSubmit()"
            @keydown.ctrl.enter.prevent="handleSubmit()"
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
              <div v-if="showModelMenu" class="agent-dock-composer__menu">
                <p class="agent-dock-composer__menu-caption">Runtime</p>
                <button
                  type="button"
                  class="agent-dock-composer__menu-item agent-dock-composer__menu-item--selected"
                >
                  <span>{{ runtimeDetail }}</span>
                  <small>Current live runtime</small>
                </button>
                <p class="agent-dock-composer__menu-note">{{ runtimeHint }}</p>
              </div>
            </div>

            <div class="agent-dock-composer__tool-group">
              <button
                type="button"
                class="agent-dock-composer__tool agent-dock-composer__tool--mode"
                :class="{ 'is-active': showModeMenu }"
                :data-mode="composerMode"
                :title="activeMode.hint"
                :aria-label="`Conversation mode: ${activeMode.label}`"
                @click="toggleSection('mode')"
              >
                <span class="agent-dock-composer__tool-icon" aria-hidden="true">{{ activeMode.icon }}</span>
                <span class="agent-dock-composer__tool-label">{{ activeMode.label }}</span>
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
