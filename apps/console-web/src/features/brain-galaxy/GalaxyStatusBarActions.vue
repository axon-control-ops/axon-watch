<script setup lang="ts">
import { operatorTerminalChipLabel } from '../../lib/workbench-terminal-panel-view';

defineProps<{
  terminalVisible: boolean;
  terminalDockAlive: boolean;
  terminalRunPhase: string | null | undefined;
  terminalPanelTitle: string;
  terminalPanelAriaLabel: string;
}>();

const emit = defineEmits<{
  resetView: [];
  switchGrid: [];
  toggleTerminal: [];
}>();
</script>

<template>
  <div class="status-bar-mockup__galaxy-actions-inner" role="group" aria-label="Galaxy view controls">
    <button
      type="button"
      class="status-bar-mockup__chip status-bar-mockup__chip--galaxy"
      title="Fit camera and clear selection"
      @click="emit('resetView')"
    >
      <span class="status-bar-mockup__chip-label">Fit</span>
    </button>
    <button
      type="button"
      class="status-bar-mockup__chip status-bar-mockup__chip--galaxy"
      title="Switch to grid mission control"
      @click="emit('switchGrid')"
    >
      <span class="status-bar-mockup__chip-label">Grid</span>
    </button>
    <button
      type="button"
      class="status-bar-mockup__chip status-bar-mockup__chip--galaxy"
      :class="{
        'status-bar-mockup__chip--galaxy-accent': !terminalVisible,
        'status-bar-mockup__chip--galaxy-alive': terminalDockAlive,
        'status-bar-mockup__chip--galaxy-executing':
          !terminalVisible && terminalRunPhase === 'executing',
        'status-bar-mockup__chip--galaxy-review-ready':
          !terminalVisible && terminalRunPhase === 'review_ready',
      }"
      :title="terminalPanelTitle"
      :aria-label="terminalPanelAriaLabel"
      @click="emit('toggleTerminal')"
    >
      <span
        class="status-bar-mockup__dot"
        :class="{
          'status-bar-mockup__dot--warn': !terminalVisible && !terminalDockAlive,
          'status-bar-mockup__dot--alive': terminalDockAlive,
        }"
        aria-hidden="true"
      />
      <span class="status-bar-mockup__chip-label">{{
        operatorTerminalChipLabel(terminalVisible)
      }}</span>
    </button>
  </div>
</template>
