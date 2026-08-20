<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue';

import { OPERATOR_PERSONA_NAME } from '../../lib/operator-persona-name';
import {
  buildVaxonComposerSubmission,
  shouldSubmitVaxonComposer,
  type VaxonExecutiveComposerMode,
  vaxonComposerSubmissionIntent,
} from '../../lib/vaxon-executive-composer';
import {
  VAXON_QUICK_PROMPTS,
  vaxonComposerAutoGrowHeight,
} from '../../lib/vaxon-super-composer';
import { useShellStore } from '../../stores/shell';
import VaxonConversationAttachControls from '../../features/kairo-conversation/VaxonConversationAttachControls.vue';
import { useVaxonConversationAttachments } from '../../features/kairo-conversation/use-vaxon-conversation-attachments';
import type { ComposerClipboardImage } from '../../lib/composer-clipboard-paste';
import type { ClaudeCatalogRow } from '../../lib/claude-catalog-view';

const props = withDefaults(
  defineProps<{
    pending: boolean;
    micLive: boolean;
    micSupported: boolean;
    privacyBlocked?: boolean;
    focusedWorkspaceLabel: string | null;
    activityLabel?: string | null;
    activityPhase?: string | null;
    captureError?: string | null;
    voiceGateFeedback?: string | null;
    layout?: 'dock' | 'center';
  }>(),
  {
    layout: 'center',
  },
);

const emit = defineEmits<{
  submit: [payload: { content: string; submissionIntent: 'ask' | 'dispatch'; attachments?: ComposerClipboardImage[] }];
  toggleMic: [];
}>();

const shell = useShellStore();
const attachments = useVaxonConversationAttachments();

const draft = ref('');
const mode = ref<VaxonExecutiveComposerMode>('ask');
const composerInput = ref<HTMLTextAreaElement | null>(null);
const composerRoot = ref<HTMLElement | null>(null);
const promptHistory = ref<string[]>([]);
const historyIndex = ref(-1);
const showRuntimeMenu = ref(false);
const showModelSection = ref(false);

const allTargets = computed(() => [
  ...(shell.runtimeStatus?.local ?? []),
  ...(shell.runtimeStatus?.cloud ?? []),
]);

const runtimeLabel = computed(() => shell.composerRuntimeLabel || 'Auto');

const selectedFamily = computed(() => {
  const target = allTargets.value.find((row) => row.id === shell.selectedRuntimeTargetId);
  return target?.family ?? 'cursor';
});

const modelRows = computed(() => {
  if (selectedFamily.value === 'claude') return shell.claudeCatalogRows;
  if (selectedFamily.value === 'codex') return shell.codexCatalogRows;
  return shell.cursorCatalogRows;
});

const isClaudeFamily = computed(() => selectedFamily.value === 'claude');

const isActive = computed(() => props.pending || props.micLive);

const activityText = computed(() => {
  if (props.activityLabel) return props.activityLabel;
  if (props.pending) return `${OPERATOR_PERSONA_NAME} · Working…`;
  return '';
});

const phaseTag = computed(() => {
  if (props.activityPhase === 'thinking' || props.pending) return 'thinking';
  if (props.activityPhase === 'speaking') return 'speaking';
  if (props.activityPhase === 'autonomous') return 'auto';
  return 'standby';
});

const placeholder = computed(() =>
  mode.value === 'dispatch'
    ? 'State the objective, success criteria, constraints, and deliverables…'
    : `Command ${OPERATOR_PERSONA_NAME} — analysis, status, routing, or a recommendation…`,
);

const submitLabel = computed(() =>
  mode.value === 'dispatch' ? 'Dispatch mission' : `Ask ${OPERATOR_PERSONA_NAME}`,
);

const micDisabled = computed(
  () => !props.micSupported || props.pending || Boolean(props.privacyBlocked),
);

const hasAttachments = computed(() => attachments.pendingAttachments.value.length > 0);

const isCenterLayout = computed(() => props.layout === 'center');

function selectRuntime(id: string): void {
  shell.setSelectedRuntimeTarget(id);
  showModelSection.value = false;
}

function selectModel(id: string): void {
  shell.setSelectedComposerModel(id);
  showRuntimeMenu.value = false;
  showModelSection.value = false;
}

function toggleRuntimeMenu(): void {
  showRuntimeMenu.value = !showRuntimeMenu.value;
  if (!showRuntimeMenu.value) showModelSection.value = false;
}

function handleDocumentClick(event: MouseEvent): void {
  if (!composerRoot.value?.contains(event.target as Node)) {
    showRuntimeMenu.value = false;
    showModelSection.value = false;
  }
}

onMounted(() => document.addEventListener('click', handleDocumentClick, { capture: true }));
onUnmounted(() => document.removeEventListener('click', handleDocumentClick, { capture: true }));

function syncEditorHeight(): void {
  const editor = composerInput.value;
  if (!editor) return;
  vaxonComposerAutoGrowHeight(editor, isCenterLayout.value ? 280 : 180);
}

watch(draft, () => syncEditorHeight());

function submit(content?: string, modeValue = mode.value): void {
  const raw = (content ?? draft.value).trim();
  if (!raw && !hasAttachments.value) return;
  if (props.pending) return;
  const message = content === undefined ? buildVaxonComposerSubmission(raw, modeValue) : raw;
  const pendingFiles = [...attachments.pendingAttachments.value];
  if (raw && (promptHistory.value.length === 0 || promptHistory.value[0] !== raw)) {
    promptHistory.value = [raw, ...promptHistory.value.slice(0, 49)];
  }
  historyIndex.value = -1;
  draft.value = '';
  showRuntimeMenu.value = false;
  showModelSection.value = false;
  attachments.clearAttachments();
  void nextTick(() => syncEditorHeight());
  emit('submit', {
    content: message,
    submissionIntent: vaxonComposerSubmissionIntent(modeValue),
    attachments: pendingFiles.length ? pendingFiles : undefined,
  });
}

function applyQuickPrompt(prompt: (typeof VAXON_QUICK_PROMPTS)[number]): void {
  mode.value = prompt.mode;
  draft.value = prompt.prompt;
  void nextTick(() => {
    composerInput.value?.focus();
    syncEditorHeight();
  });
}

function selectMode(nextMode: VaxonExecutiveComposerMode): void {
  mode.value = nextMode;
  void nextTick(() => {
    composerInput.value?.focus();
    syncEditorHeight();
  });
}

function handleKeydown(event: KeyboardEvent): void {
  if (shouldSubmitVaxonComposer(event) && (draft.value.trim() || hasAttachments.value) && !props.pending) {
    event.preventDefault();
    submit();
    return;
  }
  if (event.key === 'ArrowUp' && !event.shiftKey && !event.isComposing && promptHistory.value.length > 0) {
    const textarea = composerInput.value;
    if (textarea && textarea.selectionStart === 0 && textarea.selectionEnd === 0) {
      event.preventDefault();
      const next = Math.min(historyIndex.value + 1, promptHistory.value.length - 1);
      historyIndex.value = next;
      draft.value = promptHistory.value[next] ?? '';
      void nextTick(() => {
        textarea.selectionStart = textarea.selectionEnd = textarea.value.length;
        syncEditorHeight();
      });
    }
  }
  if (event.key === 'ArrowDown' && !event.shiftKey && historyIndex.value >= 0) {
    event.preventDefault();
    const prev = historyIndex.value - 1;
    historyIndex.value = prev;
    draft.value = prev < 0 ? '' : (promptHistory.value[prev] ?? '');
    void nextTick(() => syncEditorHeight());
  }
}

function handlePaste(event: ClipboardEvent): void {
  attachments.handlePaste(event);
}

function handleDrop(event: DragEvent): void {
  attachments.handleDrop(event);
}
</script>

<template>
  <div
    ref="composerRoot"
    class="vaxon-super-composer"
    :class="{
      'vaxon-super-composer--center': isCenterLayout,
      'vaxon-super-composer--dock': !isCenterLayout,
      'vaxon-super-composer--live': micLive,
      'vaxon-super-composer--working': pending,
    }"
    data-vaxon-composer-reply="true"
    @drop.prevent="handleDrop"
    @dragover.prevent
  >
    <div class="vaxon-super-composer__halo" aria-hidden="true" />

    <div
      v-if="isActive && activityText"
      class="vaxon-super-composer__activity"
      :data-phase="phaseTag"
      role="status"
      aria-live="polite"
    >
      <span class="vaxon-super-composer__activity-pulse" aria-hidden="true" />
      <span class="vaxon-super-composer__activity-text">{{ activityText }}</span>
      <span class="vaxon-super-composer__activity-tag">{{ phaseTag }}</span>
    </div>

    <div
      v-if="captureError || voiceGateFeedback"
      class="vaxon-super-composer__notice"
      role="alert"
    >
      <span class="vaxon-super-composer__notice-rail" aria-hidden="true" />
      <p class="vaxon-super-composer__notice-copy">{{ captureError || voiceGateFeedback }}</p>
    </div>

    <div class="vaxon-super-composer__quick-row" role="group" aria-label="Quick executive prompts">
      <button
        v-for="prompt in VAXON_QUICK_PROMPTS"
        :key="prompt.id"
        type="button"
        class="vaxon-super-composer__quick"
        :class="{ 'vaxon-super-composer__quick--dispatch': prompt.mode === 'dispatch' }"
        :disabled="pending"
        :title="prompt.hint ?? prompt.label"
        @click="applyQuickPrompt(prompt)"
      >
        {{ prompt.label }}
      </button>
    </div>

    <VaxonConversationAttachControls
      v-if="hasAttachments"
      :attachments="attachments.pendingAttachments.value"
      :disabled="pending"
      chips-only
      @remove="attachments.removeAttachment($event)"
    />

    <form class="vaxon-super-composer__form" @submit.prevent="submit()">
      <div class="vaxon-super-composer__shell">
        <div class="vaxon-super-composer__mark-wrap" aria-hidden="true">
          <span class="vaxon-super-composer__mark">V</span>
          <span v-if="micLive" class="vaxon-super-composer__voice-bars">
            <span /><span /><span /><span /><span />
          </span>
        </div>

        <textarea
          ref="composerInput"
          v-model="draft"
          rows="1"
          autocomplete="off"
          class="vaxon-super-composer__input"
          :placeholder="placeholder"
          :disabled="pending"
          :aria-label="`${OPERATOR_PERSONA_NAME} executive command input`"
          @keydown="handleKeydown"
          @paste="handlePaste"
          @input="syncEditorHeight"
        />

        <div class="vaxon-super-composer__actions">
          <button
            type="button"
            class="vaxon-super-composer__mic"
            :data-live="micLive ? 'true' : 'false'"
            :disabled="micDisabled"
            :title="micLive ? 'Stop listening' : 'Speak executive intent'"
            :aria-pressed="micLive"
            @click="emit('toggleMic')"
          >
            <span aria-hidden="true">{{ micLive ? '●' : '◌' }}</span>
            <span class="vaxon-super-composer__sr-only">
              {{ micLive ? 'Stop listening' : 'Speak executive intent' }}
            </span>
          </button>
          <button
            type="submit"
            class="vaxon-super-composer__send"
            :disabled="pending || (!draft.trim() && !hasAttachments)"
          >
            <span class="vaxon-super-composer__send-label">{{ pending ? 'Working…' : submitLabel }}</span>
            <span class="vaxon-super-composer__send-icon" aria-hidden="true">↗</span>
          </button>
        </div>
      </div>
    </form>

    <footer class="vaxon-super-composer__footer" aria-label="Executive composer controls">
      <div class="vaxon-super-composer__modes" role="group" aria-label="Submission mode">
        <button
          type="button"
          class="vaxon-super-composer__mode"
          :data-active="mode === 'ask' ? 'true' : 'false'"
          :disabled="pending"
          title="Ask VAXON for information only"
          @click="selectMode('ask')"
        >
          Ask
        </button>
        <button
          type="button"
          class="vaxon-super-composer__mode vaxon-super-composer__mode--dispatch"
          :data-active="mode === 'dispatch' ? 'true' : 'false'"
          :disabled="pending"
          title="Dispatch a mission for specialist routing"
          @click="selectMode('dispatch')"
        >
          Dispatch
        </button>
      </div>

      <div class="vaxon-super-composer__runtime-wrap">
        <button
          type="button"
          class="vaxon-super-composer__runtime-pill"
          :class="{ 'vaxon-super-composer__runtime-pill--open': showRuntimeMenu }"
          :disabled="pending"
          :title="`Runtime: ${runtimeLabel}`"
          :aria-expanded="showRuntimeMenu"
          @click.stop="toggleRuntimeMenu"
        >
          <span class="vaxon-super-composer__runtime-icon" aria-hidden="true">⚡</span>
          <span class="vaxon-super-composer__runtime-label">{{ runtimeLabel }}</span>
          <span class="vaxon-super-composer__runtime-chevron" aria-hidden="true">▾</span>
        </button>

        <div
          v-if="showRuntimeMenu"
          class="vaxon-super-composer__runtime-menu"
          role="dialog"
          aria-label="Runtime and model selection"
          @click.stop
        >
          <p class="vaxon-super-composer__runtime-menu-heading">
            Runtime · {{ focusedWorkspaceLabel || 'Fleet' }}
          </p>
          <button
            v-for="target in allTargets"
            :key="target.id"
            type="button"
            class="vaxon-super-composer__runtime-option"
            :class="{ 'vaxon-super-composer__runtime-option--active': target.id === shell.selectedRuntimeTargetId }"
            @click="selectRuntime(target.id)"
          >
            <span class="vaxon-super-composer__runtime-option-label">{{ target.label }}</span>
            <span class="vaxon-super-composer__runtime-option-meta">
              {{ target.ready ? 'Ready' : !target.available ? 'Not installed' : 'Needs sign-in' }}
            </span>
          </button>
          <p v-if="!allTargets.length" class="vaxon-super-composer__runtime-empty">
            No runtimes — check Settings → CLI runtime.
          </p>

          <button
            type="button"
            class="vaxon-super-composer__menu-section-toggle"
            :aria-expanded="showModelSection"
            @click.stop="showModelSection = !showModelSection"
          >
            <span class="vaxon-super-composer__menu-section-label">Model</span>
            <span class="vaxon-super-composer__menu-section-value">{{ shell.selectedComposerModel || 'Auto' }}</span>
            <span aria-hidden="true">{{ showModelSection ? '▴' : '▾' }}</span>
          </button>

          <div v-if="showModelSection" class="vaxon-super-composer__model-list">
            <button
              v-for="row in modelRows"
              :key="row.id"
              type="button"
              class="vaxon-super-composer__model-option"
              :class="{ 'vaxon-super-composer__model-option--active': row.id === shell.selectedComposerModel }"
              :disabled="!row.available"
              @click="selectModel(row.id)"
            >
              <span class="vaxon-super-composer__model-option-label">
                {{ row.label }}
                <span v-if="row.badge" class="vaxon-super-composer__model-badge">{{ row.badge }}</span>
                <span
                  v-if="isClaudeFamily && (row as ClaudeCatalogRow).effort"
                  class="vaxon-super-composer__model-effort"
                  :data-effort="(row as ClaudeCatalogRow).effort"
                >{{ (row as ClaudeCatalogRow).effort }}</span>
              </span>
              <small class="vaxon-super-composer__model-option-desc">{{ row.description }}</small>
            </button>
            <p v-if="!modelRows.length" class="vaxon-super-composer__runtime-empty">
              No models available for this runtime.
            </p>
          </div>
        </div>
      </div>

      <VaxonConversationAttachControls
        :attachments="attachments.pendingAttachments.value"
        :disabled="pending"
        button-only
        @attach="attachments.pickFiles()"
      />

      <span class="vaxon-super-composer__context-copy">
        {{ focusedWorkspaceLabel || 'Fleet' }}
        <span aria-hidden="true">·</span>
        Enter send · Shift+Enter newline · ↑ history
      </span>

      <button
        type="button"
        class="vaxon-super-composer__brief"
        :disabled="pending"
        @click="submit('REPORT', 'ask')"
      >
        Brief now
      </button>
    </footer>
  </div>
</template>

<style scoped src="./vaxon-super-composer.css"></style>
