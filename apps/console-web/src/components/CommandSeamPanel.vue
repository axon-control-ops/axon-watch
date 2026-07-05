<script setup lang="ts">
import { nextTick, onMounted, ref, watch } from 'vue';

import { resizeCommandComposer } from '../lib/command-composer-autosize';
import { useShellStore } from '../stores/shell';

const props = withDefaults(
  defineProps<{
    compact?: boolean;
    placeholder?: string;
  }>(),
  {
    compact: true,
    placeholder: 'Describe the next operator action…',
  },
);

const shell = useShellStore();
const inputRef = ref<HTMLTextAreaElement | null>(null);

function syncComposerHeight(): void {
  if (!inputRef.value) {
    return;
  }

  resizeCommandComposer(inputRef.value, { compact: props.compact });
}

function handleSubmit(event: Event): void {
  event.preventDefault();
  shell.submitOperatorCommand();
}

watch(
  () => shell.operatorCommandDraft,
  () => {
    void nextTick(syncComposerHeight);
  },
);

watch(
  () => props.compact,
  () => {
    void nextTick(syncComposerHeight);
  },
);

onMounted(() => {
  syncComposerHeight();
});
</script>

<template>
  <form
    class="command-seam"
    :class="{ 'command-seam--compact': compact, 'command-seam--autosize': true }"
    @submit="handleSubmit"
  >
    <div class="command-seam__composer">
      <textarea
        id="operator-command-input"
        ref="inputRef"
        v-model="shell.operatorCommandDraft"
        class="command-seam__input"
        rows="2"
        aria-label="Operator command"
        :placeholder="props.placeholder"
        :disabled="!shell.currentWorkspace"
        @input="syncComposerHeight"
        @keydown.meta.enter.prevent="shell.submitOperatorCommand()"
        @keydown.ctrl.enter.prevent="shell.submitOperatorCommand()"
      />
      <button
        type="submit"
        class="command-seam__send"
        :disabled="!shell.canSubmitOperatorCommand"
        :aria-label="shell.commandMutationState === 'submitting' ? 'Sending command' : 'Send command'"
      >
        <span v-if="shell.commandMutationState === 'submitting'" class="command-seam__send-spinner" aria-hidden="true" />
        <span v-else class="command-seam__send-icon" aria-hidden="true">↑</span>
      </button>
    </div>
    <p v-if="!shell.currentWorkspace" class="command-seam__empty">
      Select a workspace to send commands.
    </p>
    <p v-if="shell.commandMutationError" class="command-seam__error">
      {{ shell.commandMutationError }}
    </p>
  </form>
</template>
