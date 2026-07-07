<script setup lang="ts">
import { computed } from 'vue';

import { buildOperatorIncidentFeed } from '../../lib/operator-incident-feed-view';
import { useShellStore } from '../../stores/shell';

const shell = useShellStore();

const feedView = computed(() =>
  buildOperatorIncidentFeed({
    topSignals: shell.operatorBriefing?.top_signals ?? [],
    workspaceId: shell.currentWorkspace?.workspace_id ?? null,
    fleetHealth: shell.operatorFleetHealth,
  }),
);

function focusSignal(signalId: string): void {
  shell.focusAttentionSidebar(signalId);
}
</script>

<template>
  <section class="operator-incident-feed" aria-label="Incident feed">
    <header class="operator-incident-feed__header">
      <div>
        <p class="operator-incident-feed__eyebrow">Unified inbox</p>
        <h3 class="operator-incident-feed__title">Incidents</h3>
      </div>
      <span class="operator-incident-feed__headline">{{ feedView.headline }}</span>
    </header>

    <ul v-if="feedView.items.length" class="operator-incident-feed__list">
      <li
        v-for="item in feedView.items"
        :key="item.id"
        class="operator-incident-feed__item"
        :class="`operator-incident-feed__item--${item.severity}`"
      >
        <button type="button" class="operator-incident-feed__button" @click="focusSignal(item.id)">
          <span class="operator-incident-feed__item-title">{{ item.title }}</span>
          <span class="operator-incident-feed__item-summary">{{ item.summary }}</span>
          <span class="operator-incident-feed__item-meta">
            {{ item.source === 'fleet' ? 'Fleet rollup' : 'Signal inbox' }}
          </span>
        </button>
      </li>
    </ul>
    <p v-else class="operator-incident-feed__empty">{{ feedView.emptyCopy }}</p>
  </section>
</template>
