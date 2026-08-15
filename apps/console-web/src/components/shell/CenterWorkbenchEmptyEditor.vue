<script setup lang="ts">
import { computed, ref } from 'vue';

import {
  buildIdeEmptyEditorView,
  type IdeEmptyEditorStepAction,
} from '../../lib/ide-empty-editor-view';

const props = defineProps<{
  hasWorkspace: boolean;
}>();

const emit = defineEmits<{
  openExplorer: [];
  openSearch: [];
  createNewFile: [];
  showAgent: [];
}>();

const blockedReason = ref<string | null>(null);

const view = computed(() =>
  buildIdeEmptyEditorView({ hasWorkspace: props.hasWorkspace }),
);

function blockedMessage(action: IdeEmptyEditorStepAction): string | null {
  if (action === 'new-file' && !props.hasWorkspace) {
    return 'Select a workspace before creating a file.';
  }
  if (action === 'search' && !props.hasWorkspace) {
    return 'Select a workspace before searching files.';
  }
  return null;
}

function handleStepClick(action: IdeEmptyEditorStepAction | undefined): void {
  blockedReason.value = null;
  if (!action) {
    blockedReason.value = 'Use the workspace picker in the top bar for this step.';
    return;
  }

  const blocked = blockedMessage(action);
  if (blocked) {
    blockedReason.value = blocked;
    return;
  }

  if (action === 'explorer') {
    emit('openExplorer');
    return;
  }
  if (action === 'search') {
    emit('openSearch');
    return;
  }
  if (action === 'new-file') {
    emit('createNewFile');
    return;
  }
  if (action === 'agent') {
    emit('showAgent');
  }
}
</script>

<template>
  <section class="center-workbench__empty-editor" aria-label="Editor getting started">
    <p class="center-workbench__empty-editor-title">{{ view.title }}</p>
    <p class="center-workbench__empty-editor-subtitle">{{ view.subtitle }}</p>
    <p
      v-if="blockedReason"
      class="center-workbench__empty-editor-blocked"
      role="status"
      aria-live="polite"
    >
      {{ blockedReason }}
    </p>
    <ol class="center-workbench__empty-editor-steps">
      <li
        v-for="step in view.steps"
        :key="step.label"
        class="center-workbench__empty-editor-step"
      >
        <button
          type="button"
          class="center-workbench__empty-editor-step-btn"
          :class="{ 'center-workbench__empty-editor-step-btn--static': !step.action }"
          :disabled="Boolean(step.action && blockedMessage(step.action))"
          :aria-disabled="Boolean(step.action && blockedMessage(step.action))"
          @click="handleStepClick(step.action)"
        >
          <span class="center-workbench__empty-editor-step-label">{{ step.label }}</span>
          <span class="center-workbench__empty-editor-step-detail">{{ step.detail }}</span>
          <span v-if="step.shortcut" class="center-workbench__empty-editor-step-shortcut">
            {{ step.shortcut }}
          </span>
        </button>
      </li>
    </ol>
  </section>
</template>
