<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref } from 'vue';

import { OPERATOR_PERSONA_NAME } from '../../lib/operator-persona-name';
import {
  buildVaxonComposerSubmission,
  shouldSubmitVaxonComposer,
  type VaxonExecutiveComposerMode,
  vaxonComposerSubmissionIntent,
} from '../../lib/vaxon-executive-composer';
import { useShellStore } from '../../stores/shell';
import VaxonConversationAttachControls from '../../features/kairo-conversation/VaxonConversationAttachControls.vue';
import { useVaxonConversationAttachments } from '../../features/kairo-conversation/use-vaxon-conversation-attachments';
import type { ComposerClipboardImage } from '../../lib/composer-clipboard-paste';
import type { ClaudeCatalogRow } from '../../lib/claude-catalog-view';

const props = defineProps<{
  pending: boolean;
  micLive: boolean;
  micSupported: boolean;
  privacyBlocked?: boolean;
  focusedWorkspaceLabel: string | null;
  activityLabel?: string | null;
  activityPhase?: string | null;
}>();

const emit = defineEmits<{
  submit: [payload: { content: string; submissionIntent: 'ask' | 'dispatch'; attachments?: ComposerClipboardImage[] }];
  toggleMic: [];
}>();

const shell = useShellStore();
const attachments = useVaxonConversationAttachments();

const draft = ref('');
const mode = ref<VaxonExecutiveComposerMode>('ask');
const expanded = ref(false);
const composerInput = ref<HTMLTextAreaElement | null>(null);
const composerRoot = ref<HTMLElement | null>(null);

// ── Prompt history (in-session, retained across sends) ────────────────────
const promptHistory = ref<string[]>([]);
const historyIndex = ref(-1);

// ── Runtime / model menu ─────────────────────────────────────────────────────
const showRuntimeMenu = ref(false);
const showModelSection = ref(false);

const allTargets = computed(() => [
  ...(shell.runtimeStatus?.local ?? []),
  ...(shell.runtimeStatus?.cloud ?? []),
]);

const runtimeLabel = computed(() => shell.composerRuntimeLabel || 'Auto');

const selectedFamily = computed(() => {
  const t = allTargets.value.find((r) => r.id === shell.selectedRuntimeTargetId);
  return t?.family ?? 'cursor';
});

const modelRows = computed(() => {
  if (selectedFamily.value === 'claude') return shell.claudeCatalogRows;
  if (selectedFamily.value === 'codex') return shell.codexCatalogRows;
  return shell.cursorCatalogRows;
});

const isClaudeFamily = computed(() => selectedFamily.value === 'claude');

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

// Click-outside closes the menu
function handleDocumentClick(event: MouseEvent): void {
  if (!composerRoot.value?.contains(event.target as Node)) {
    showRuntimeMenu.value = false;
    showModelSection.value = false;
  }
}

onMounted(() => document.addEventListener('click', handleDocumentClick, { capture: true }));
onUnmounted(() => document.removeEventListener('click', handleDocumentClick, { capture: true }));

// ── Activity strip ───────────────────────────────────────────────────────────
const isActive = computed(
  () => props.pending || Boolean(props.activityLabel) || Boolean(props.activityPhase),
);

const activityText = computed(() => {
  if (props.activityLabel) return props.activityLabel;
  if (props.activityPhase) return `${OPERATOR_PERSONA_NAME} · ${props.activityPhase}`;
  if (props.pending) return `${OPERATOR_PERSONA_NAME} · Working…`;
  return '';
});

const phaseTag = computed(() => {
  const p = props.activityPhase ?? '';
  if (p === 'thinking') return 'thinking';
  if (p === 'speaking') return 'speaking';
  if (p === 'autonomous') return 'auto';
  if (props.pending) return 'working';
  return 'standby';
});

// ── Composer ─────────────────────────────────────────────────────────────────
const placeholder = computed(() =>
  mode.value === 'dispatch'
    ? 'State the objective, success criteria, constraints, or deliverables…'
    : `Ask ${OPERATOR_PERSONA_NAME} for analysis, status, or a recommendation…`,
);

const submitLabel = computed(() =>
  mode.value === 'dispatch' ? 'Dispatch' : `Ask ${OPERATOR_PERSONA_NAME}`,
);

const micDisabled = computed(
  () => !props.micSupported || props.pending || Boolean(props.privacyBlocked),
);

const hasAttachments = computed(() => attachments.pendingAttachments.value.length > 0);

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
  expanded.value = false;
  showRuntimeMenu.value = false;
  showModelSection.value = false;
  attachments.clearAttachments();
  emit('submit', {
    content: message,
    submissionIntent: vaxonComposerSubmissionIntent(modeValue),
    attachments: pendingFiles.length ? pendingFiles : undefined,
  });
}

function selectMode(nextMode: VaxonExecutiveComposerMode): void {
  mode.value = nextMode;
  void nextTick(() => composerInput.value?.focus());
}

async function toggleExpanded(): Promise<void> {
  expanded.value = !expanded.value;
  await nextTick();
  composerInput.value?.focus();
}

function handleKeydown(event: KeyboardEvent): void {
  if (shouldSubmitVaxonComposer(event) && (draft.value.trim() || hasAttachments.value) && !props.pending) {
    event.preventDefault();
    submit();
    return;
  }
  // Arrow-up / Arrow-down to browse prompt history (only when on single line)
  if (event.key === 'ArrowUp' && !event.shiftKey && !event.isComposing && promptHistory.value.length > 0) {
    const textarea = composerInput.value;
    if (textarea && textarea.selectionStart === 0 && textarea.selectionEnd === 0) {
      event.preventDefault();
      const next = Math.min(historyIndex.value + 1, promptHistory.value.length - 1);
      historyIndex.value = next;
      draft.value = promptHistory.value[next] ?? '';
      void nextTick(() => {
        textarea.selectionStart = textarea.selectionEnd = textarea.value.length;
      });
    }
  }
  if (event.key === 'ArrowDown' && !event.shiftKey && !event.isComposing && historyIndex.value >= 0) {
    event.preventDefault();
    const prev = historyIndex.value - 1;
    historyIndex.value = prev;
    draft.value = prev < 0 ? '' : (promptHistory.value[prev] ?? '');
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
    class="mc-live-ops__reply"
    data-vaxon-composer-reply="true"
    :class="{ 'mc-live-ops__reply--expanded': expanded }"
    @drop.prevent="handleDrop"
    @dragover.prevent
  >
    <!-- Activity strip -->
    <div
      v-if="isActive"
      class="mc-exec-composer__activity"
      :data-phase="phaseTag"
      role="status"
      aria-live="polite"
    >
      <span class="mc-exec-composer__activity-pulse" aria-hidden="true" />
      <span class="mc-exec-composer__activity-text">{{ activityText }}</span>
      <span class="mc-exec-composer__activity-tag">{{ phaseTag }}</span>
    </div>

    <!-- Pending attachment chips -->
    <VaxonConversationAttachControls
      v-if="hasAttachments"
      :attachments="attachments.pendingAttachments.value"
      :disabled="pending"
      chips-only
      @remove="attachments.removeAttachment($event)"
    />

    <form class="mc-live-ops__reply-form" @submit.prevent="submit()">
      <div class="mc-exec-composer__input-row">
        <span class="mc-exec-composer__mark" aria-hidden="true">V</span>
        <textarea
          ref="composerInput"
          v-model="draft"
          :rows="expanded ? 3 : 1"
          autocomplete="off"
          :placeholder="placeholder"
          :disabled="pending"
          :aria-label="`${OPERATOR_PERSONA_NAME} ask or dispatch input`"
          @keydown="handleKeydown"
          @paste="handlePaste"
        />
        <button
          type="button"
          class="mc-live-ops__mic"
          :data-live="micLive ? 'true' : 'false'"
          :disabled="micDisabled"
          :title="micLive ? 'Stop listening' : 'Speak executive intent'"
          :aria-pressed="micLive"
          @click="emit('toggleMic')"
        >
          <span aria-hidden="true">{{ micLive ? '●' : '◌' }}</span>
          <span class="mc-exec-composer__sr-only">
            {{ micLive ? 'Stop listening' : 'Speak executive intent' }}
          </span>
        </button>
        <button
          type="submit"
          class="mc-live-ops__send"
          :disabled="pending || (!draft.trim() && !hasAttachments)"
        >
          <span class="mc-exec-composer__send-label">{{ pending ? 'Working…' : submitLabel }}</span>
          <span class="mc-exec-composer__send-icon" aria-hidden="true">↗</span>
        </button>
      </div>
    </form>

    <footer class="mc-exec-composer__context" aria-label="Mission composer context">
      <div class="mc-exec-composer__modes" role="group" aria-label="Submission mode">
        <button
          type="button"
          class="mc-exec-composer__mode"
          :data-active="mode === 'ask' ? 'true' : 'false'"
          :disabled="pending"
          title="Ask VAXON for information only"
          @click="selectMode('ask')"
        >
          Ask
        </button>
        <button
          type="button"
          class="mc-exec-composer__mode"
          :data-active="mode === 'dispatch' ? 'true' : 'false'"
          :disabled="pending"
          title="Dispatch a mission for specialist routing"
          @click="selectMode('dispatch')"
        >
          Dispatch
        </button>
      </div>

      <!-- Runtime + model picker pill -->
      <div class="mc-exec-composer__runtime-wrap">
        <button
          type="button"
          class="mc-exec-composer__runtime-pill"
          :class="{ 'mc-exec-composer__runtime-pill--open': showRuntimeMenu }"
          :disabled="pending"
          :title="`Runtime: ${runtimeLabel}`"
          :aria-expanded="showRuntimeMenu"
          @click.stop="toggleRuntimeMenu"
        >
          <span class="mc-exec-composer__runtime-icon" aria-hidden="true">⚡</span>
          <span class="mc-exec-composer__runtime-label">{{ runtimeLabel }}</span>
          <span class="mc-exec-composer__runtime-chevron" aria-hidden="true">▾</span>
        </button>

        <div
          v-if="showRuntimeMenu"
          class="mc-exec-composer__runtime-menu"
          role="dialog"
          aria-label="Runtime and model selection"
          @click.stop
        >
          <!-- Runtime targets -->
          <p class="mc-exec-composer__runtime-menu-heading">Runtime · {{ focusedWorkspaceLabel || 'Fleet' }}</p>
          <button
            v-for="target in allTargets"
            :key="target.id"
            type="button"
            class="mc-exec-composer__runtime-option"
            :class="{ 'mc-exec-composer__runtime-option--active': target.id === shell.selectedRuntimeTargetId }"
            @click="selectRuntime(target.id)"
          >
            <span class="mc-exec-composer__runtime-option-label">{{ target.label }}</span>
            <span class="mc-exec-composer__runtime-option-meta">
              {{ target.ready ? 'Ready' : !target.available ? 'Not installed' : 'Needs sign-in' }}
            </span>
          </button>
          <p v-if="!allTargets.length" class="mc-exec-composer__runtime-empty">
            No runtimes — check Settings → CLI runtime.
          </p>

          <!-- Model catalog -->
          <button
            type="button"
            class="mc-exec-composer__menu-section-toggle"
            :aria-expanded="showModelSection"
            @click.stop="showModelSection = !showModelSection"
          >
            <span class="mc-exec-composer__menu-section-label">Model</span>
            <span class="mc-exec-composer__menu-section-value">{{ shell.selectedComposerModel || 'Auto' }}</span>
            <span aria-hidden="true">{{ showModelSection ? '▴' : '▾' }}</span>
          </button>

          <div v-if="showModelSection" class="mc-exec-composer__model-list">
            <button
              v-for="row in modelRows"
              :key="row.id"
              type="button"
              class="mc-exec-composer__model-option"
              :class="{ 'mc-exec-composer__model-option--active': row.id === shell.selectedComposerModel }"
              :disabled="!row.available"
              @click="selectModel(row.id)"
            >
              <span class="mc-exec-composer__model-option-label">
                {{ row.label }}
                <span v-if="row.badge" class="mc-exec-composer__model-badge">{{ row.badge }}</span>
                <span
                  v-if="isClaudeFamily && (row as ClaudeCatalogRow).effort"
                  class="mc-exec-composer__model-effort"
                  :data-effort="(row as ClaudeCatalogRow).effort"
                >{{ (row as ClaudeCatalogRow).effort }}</span>
              </span>
              <small class="mc-exec-composer__model-option-desc">{{ row.description }}</small>
            </button>
            <p v-if="!modelRows.length" class="mc-exec-composer__runtime-empty">
              No models available for this runtime.
            </p>
          </div>
        </div>
      </div>

      <!-- Attach button -->
      <VaxonConversationAttachControls
        :attachments="attachments.pendingAttachments.value"
        :disabled="pending"
        button-only
        @attach="attachments.pickFiles()"
      />

      <span class="mc-exec-composer__context-copy">
        {{ focusedWorkspaceLabel || 'Fleet' }}
        <span aria-hidden="true">·</span>
        {{ expanded ? 'Shift+Enter for a new line' : 'Enter to send' }}
      </span>
      <button
        type="button"
        class="mc-exec-composer__expand"
        :aria-expanded="expanded"
        :disabled="pending"
        @click="void toggleExpanded()"
      >
        {{ expanded ? 'Compact' : 'Details' }}
      </button>
      <button
        v-if="expanded"
        type="button"
        class="mc-exec-composer__brief"
        :disabled="pending"
        @click="submit('REPORT', 'ask')"
      >
        Brief
      </button>
    </footer>
  </div>
</template>

<style scoped src="./mission-control-executive-composer.css"></style>
