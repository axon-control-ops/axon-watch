<script setup lang="ts">
import { useShellStore } from '../stores/shell';

const shell = useShellStore();

function handleSubmit(event: Event): void {
  event.preventDefault();
  shell.submitOperatorCommand();
}
</script>

<template>
  <form class="command-seam" @submit="handleSubmit">
    <div class="command-seam__composer">
      <textarea
        id="operator-command-input"
        v-model="shell.operatorCommandDraft"
        class="command-seam__input"
        rows="2"
        aria-label="Operator command"
        placeholder="Describe the next operator action…"
        :disabled="!shell.currentWorkspace"
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
