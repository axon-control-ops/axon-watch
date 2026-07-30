<script setup lang="ts">
import type { OperatorCenterView } from '../../lib/operator-brain-graph-view';
import {
  operatorTerminalChipLabel,
} from '../../lib/workbench-terminal-panel-view';

defineProps<{
  centerView: OperatorCenterView;
  radarTone: string;
  terminalVisible: boolean;
  terminalDockAlive: boolean;
  terminalRunPhase: string | null;
  terminalPanelTitle: string;
  terminalPanelAriaLabel: string;
  kairoTitle: string;
  kairoSubtitle: string;
  showKairoPresence?: boolean;
}>();

const emit = defineEmits<{
  setCenterView: [view: OperatorCenterView];
  toggleTerminal: [];
}>();
</script>

<template>
  <header class="operator-status-radar-panel__header">
    <div class="operator-status-radar-panel__header-copy">
      <p class="operator-status-radar-panel__eyebrow">Operator center</p>
      <h2 class="operator-status-radar-panel__title">Mission Control</h2>
    </div>
    <div class="operator-status-radar-panel__header-actions">
      <div
        class="operator-center-view-switch"
        role="group"
        aria-label="Mission Control or Brain Graph"
      >
        <button
          type="button"
          class="operator-center-view-switch__button"
          :class="{ 'operator-center-view-switch__button--active': centerView === 'grid' }"
          :aria-pressed="centerView === 'grid'"
          title="Mission Control — fleet health and Task board"
          @click="emit('setCenterView', 'grid')"
        >
          Mission Control
        </button>
        <button
          type="button"
          class="operator-center-view-switch__button"
          :class="{ 'operator-center-view-switch__button--active': centerView === 'graph' }"
          :aria-pressed="centerView === 'graph'"
          title="Brain Graph — dependency graph + LIVE OPERATIONS"
          @click="emit('setCenterView', 'graph')"
        >
          Brain Graph
        </button>
      </div>
      <button
        type="button"
        class="operator-status-radar-panel__terminal-chip"
        :class="{
          'operator-status-radar-panel__terminal-chip--collapsed': !terminalVisible,
          'operator-status-radar-panel__terminal-chip--alive': terminalDockAlive,
          'operator-status-radar-panel__terminal-chip--executing':
            !terminalVisible && terminalRunPhase === 'executing',
          'operator-status-radar-panel__terminal-chip--review-ready':
            !terminalVisible && terminalRunPhase === 'review_ready',
        }"
        :title="terminalPanelTitle"
        :aria-label="terminalPanelAriaLabel"
        @click="emit('toggleTerminal')"
      >
        {{ operatorTerminalChipLabel(terminalVisible) }}
        <span
          v-if="terminalDockAlive"
          class="operator-status-radar-panel__terminal-chip-pulse"
          aria-hidden="true"
        />
      </button>
      <div v-if="showKairoPresence !== false" class="operator-status-radar-panel__presence">
        <span
          class="operator-status-radar-panel__status-dot"
          :class="`operator-status-radar-panel__status-dot--${radarTone}`"
          aria-hidden="true"
        />
        <div class="operator-status-radar-panel__presence-copy">
          <span class="operator-status-radar-panel__presence-title">{{ kairoTitle }}</span>
          <span class="operator-status-radar-panel__presence-subtitle">{{ kairoSubtitle }}</span>
        </div>
      </div>
    </div>
  </header>
</template>
