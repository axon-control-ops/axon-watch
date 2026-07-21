<script setup lang="ts">
import { computed } from 'vue';

import { useWorkbenchTerminalReopen } from '../../composables/useWorkbenchTerminalReopen';

const props = defineProps<{
  runPhase: string | null | undefined;
  terminalPanelVisible: boolean;
}>();

const emit = defineEmits<{ show: [] }>();

const terminalPanelVisible = computed(() => props.terminalPanelVisible);
const runPhase = computed(() => props.runPhase);
const { terminalReopenAlive, terminalReopenTitle, terminalReopenAriaLabel } =
  useWorkbenchTerminalReopen({ terminalPanelVisible, runPhase });
</script>

<template>
  <button
    type="button"
    class="workbench-terminal-reopen"
    :class="{
      'workbench-terminal-reopen--alive': terminalReopenAlive,
      'workbench-terminal-reopen--executing': runPhase === 'executing',
      'workbench-terminal-reopen--review-ready': runPhase === 'review_ready',
    }"
    :title="terminalReopenTitle"
    :aria-label="terminalReopenAriaLabel"
    @click="emit('show')"
  >
    <span class="workbench-terminal-reopen__label">TERMINAL</span>
    <span v-if="terminalReopenAlive" class="workbench-terminal-reopen__pulse" aria-hidden="true" />
  </button>
</template>
