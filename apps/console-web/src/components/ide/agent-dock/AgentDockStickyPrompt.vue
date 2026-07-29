<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue';

import OperatorMessageActions from '../../conversation/OperatorMessageActions.vue';
import {
  resendOperatorMessage,
  submitOperatorPromptInline,
} from '../../../lib/operator-message-composer-actions';
import { useShellStore } from '../../../stores/shell';

const props = withDefaults(
  defineProps<{
    text: string;
    showResend?: boolean;
  }>(),
  {
    showResend: true,
  },
);

const shell = useShellStore();
const rootRef = ref<HTMLElement | null>(null);
const editorRef = ref<HTMLTextAreaElement | null>(null);
const active = ref(false);
const editing = ref(false);
const draft = ref(props.text);
const saving = ref(false);

const modelChip = computed(() => {
  const model = String(shell.selectedComposerModel ?? '').trim();
  if (!model || model === 'auto') {
    return 'Auto';
  }
  return model.length > 28 ? `${model.slice(0, 26)}…` : model;
});

watch(
  () => props.text,
  (next) => {
    if (!editing.value) {
      draft.value = next;
    }
  },
);

async function startEdit(): Promise<void> {
  active.value = true;
  editing.value = true;
  draft.value = props.text;
  await nextTick();
  const editor = editorRef.value;
  if (!editor) {
    return;
  }
  editor.focus();
  editor.setSelectionRange(editor.value.length, editor.value.length);
  syncEditorHeight();
}

function cancelEdit(): void {
  editing.value = false;
  draft.value = props.text;
  saving.value = false;
}

async function saveEdit(): Promise<void> {
  const trimmed = draft.value.trim();
  if (!trimmed || saving.value) {
    return;
  }
  saving.value = true;
  try {
    const ok = await submitOperatorPromptInline(trimmed);
    if (ok) {
      editing.value = false;
      active.value = false;
    }
  } finally {
    saving.value = false;
  }
}

function syncEditorHeight(): void {
  const editor = editorRef.value;
  if (!editor) {
    return;
  }
  editor.style.height = 'auto';
  editor.style.height = `${Math.max(editor.scrollHeight, 44)}px`;
}

function toggleActive(event: MouseEvent): void {
  if (editing.value) {
    return;
  }
  const target = event.target as HTMLElement | null;
  if (target?.closest('.conversation-seam__message-actions')) {
    return;
  }
  if (target?.closest('.agent-dock-sticky-prompt__text')) {
    void startEdit();
    return;
  }
  active.value = !active.value;
}

function onDocumentPointerDown(event: PointerEvent): void {
  if (!rootRef.value) {
    return;
  }
  if (rootRef.value.contains(event.target as Node)) {
    return;
  }
  if (editing.value) {
    cancelEdit();
  }
  active.value = false;
}

function onKeydown(event: KeyboardEvent): void {
  if (event.key === 'Escape') {
    if (editing.value) {
      event.preventDefault();
      cancelEdit();
      return;
    }
    if (active.value) {
      active.value = false;
    }
  }
}

function onEditorKeydown(event: KeyboardEvent): void {
  if (event.key === 'Escape') {
    event.preventDefault();
    cancelEdit();
    return;
  }
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault();
    void saveEdit();
  }
}

onMounted(() => {
  document.addEventListener('pointerdown', onDocumentPointerDown, true);
});

onUnmounted(() => {
  document.removeEventListener('pointerdown', onDocumentPointerDown, true);
});
</script>

<template>
  <div
    ref="rootRef"
    class="agent-dock-sticky-prompt"
    :class="{
      'agent-dock-sticky-prompt--active': active || editing,
      'agent-dock-sticky-prompt--editing': editing,
    }"
    role="group"
    :tabindex="editing ? -1 : 0"
    aria-label="Your message"
    @click="toggleActive"
    @keydown="onKeydown"
  >
    <div
      v-if="!editing"
      class="agent-dock-sticky-prompt__chrome"
    >
      <span class="agent-dock-sticky-prompt__label">You</span>
      <OperatorMessageActions
        class="agent-dock-sticky-prompt__actions"
        variant="icons"
        :text="text"
        :show-resend="showResend"
        edit-behavior="inline"
        edit-title="Edit this message"
        edit-aria-label="Edit this message"
        @edit="startEdit"
        @resend="() => void resendOperatorMessage(text)"
      />
    </div>

    <slot name="attachments" />

    <textarea
      v-if="editing"
      ref="editorRef"
      v-model="draft"
      class="agent-dock-sticky-prompt__editor"
      rows="2"
      aria-label="Edit your message"
      @click.stop
      @input="syncEditorHeight"
      @keydown="onEditorKeydown"
    />
    <p
      v-else
      class="agent-dock-sticky-prompt__text"
      title="Click to edit"
    >
      {{ text }}
    </p>

    <div
      v-if="editing"
      class="agent-dock-sticky-prompt__footer"
      @click.stop
    >
      <div class="agent-dock-sticky-prompt__footer-meta">
        <span class="agent-dock-sticky-prompt__mode-chip" aria-hidden="true">
          <span class="agent-dock-sticky-prompt__mode-icon">∞</span>
          Agent
        </span>
        <span class="agent-dock-sticky-prompt__model-chip">{{ modelChip }}</span>
      </div>
      <div class="agent-dock-sticky-prompt__footer-actions">
        <button
          type="button"
          class="agent-dock-sticky-prompt__icon-btn"
          title="Cancel (Esc)"
          aria-label="Cancel edit"
          :disabled="saving"
          @click="cancelEdit"
        >
          <svg
            width="14"
            height="14"
            viewBox="0 0 16 16"
            fill="none"
            stroke="currentColor"
            stroke-width="1.45"
            stroke-linecap="round"
            aria-hidden="true"
          >
            <path d="M4.2 4.2l7.6 7.6M11.8 4.2l-7.6 7.6" />
          </svg>
        </button>
        <button
          type="button"
          class="agent-dock-sticky-prompt__send"
          title="Send (Enter)"
          aria-label="Send edited message"
          :disabled="saving || !draft.trim()"
          @click="saveEdit"
        >
          <span
            v-if="saving"
            class="agent-dock-sticky-prompt__send-spinner"
            aria-hidden="true"
          />
          <span
            v-else
            class="agent-dock-sticky-prompt__send-icon"
            aria-hidden="true"
          >↑</span>
        </button>
      </div>
    </div>
  </div>
</template>
