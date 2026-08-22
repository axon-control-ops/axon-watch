<script setup lang="ts">
import { computed } from 'vue';

import type { OperatorCenterView } from '../../lib/operator-brain-graph-view';
import {
  OPERATOR_CENTER_TABS,
  operatorCenterTabBadgeCount,
  operatorCenterTabMeta,
} from '../../lib/operator-center-tabs-view';
import { operatorTerminalChipLabel } from '../../lib/workbench-terminal-panel-view';

const props = defineProps<{
  centerView: OperatorCenterView;
  radarTone: string;
  terminalVisible: boolean;
  terminalDockAlive: boolean;
  terminalRunPhase: string | null;
  terminalPanelTitle: string;
  terminalPanelAriaLabel: string;
  kairoTitle: string;
  kairoSubtitle: string;
  attentionBadgeCount: number;
  dispatchQueuedCount?: number;
  openEmailCount?: number;
}>();

const emit = defineEmits<{
  setCenterView: [view: OperatorCenterView];
  toggleTerminal: [];
}>();

const tabMeta = computed(() => operatorCenterTabMeta(props.centerView));

function tabBadge(view: OperatorCenterView): number | null {
  return operatorCenterTabBadgeCount({
    view,
    attentionCount: props.attentionBadgeCount,
    dispatchQueuedCount: props.dispatchQueuedCount ?? 0,
    openEmailCount: props.openEmailCount ?? 0,
  });
}
</script>

<template>
  <header class="operator-center-shell">
    <div class="operator-center-shell__top">
      <div class="operator-center-shell__title-block">
        <p class="operator-center-shell__eyebrow">{{ tabMeta.eyebrow }}</p>
        <h2 class="operator-center-shell__title">{{ tabMeta.title }}</h2>
      </div>

      <div class="operator-center-shell__top-actions">
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

        <div
          v-if="centerView !== 'mission' && centerView !== 'vaxon'"
          class="operator-status-radar-panel__presence"
        >
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
    </div>

    <div class="operator-center-shell__tabs-scroll">
      <nav
        class="operator-center-shell__tabs"
        role="tablist"
        aria-label="Operator center views"
      >
        <button
          v-for="tab in OPERATOR_CENTER_TABS"
          :key="tab.id"
          type="button"
          class="operator-center-shell__tab"
          role="tab"
          :class="{ 'operator-center-shell__tab--active': centerView === tab.id }"
          :aria-selected="centerView === tab.id"
          :title="tab.label"
          @click="emit('setCenterView', tab.id)"
        >
          <span class="operator-center-shell__tab-label">{{ tab.label }}</span>
          <span
            v-if="tabBadge(tab.id)"
            class="operator-center-shell__tab-badge"
            :aria-label="`${tabBadge(tab.id)} items`"
          >
            {{ tabBadge(tab.id) }}
          </span>
        </button>
      </nav>
    </div>
  </header>
</template>
