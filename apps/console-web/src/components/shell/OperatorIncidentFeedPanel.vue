<script setup lang="ts">
import { computed, ref, watch } from 'vue';

import { buildOperatorIncidentFeed } from '../../lib/operator-incident-feed-view';
import HandoffToIdeButton from './HandoffToIdeButton.vue';
import { useShellStore } from '../../stores/shell';

const shell = useShellStore();
const expandedId = ref<string | null>(null);

const feedView = computed(() => {
  const spoken = shell.operatorBriefing?.operator_presence?.spoken_alert;
  return buildOperatorIncidentFeed({
    topSignals: shell.operatorBriefing?.top_signals ?? [],
    workspaceId: shell.currentWorkspace?.workspace_id ?? null,
    fleetHealth: shell.operatorFleetHealth,
    limit: 8,
    serverExplanation: spoken?.explanation ?? null,
    serverSignalId: spoken?.signal_id ?? null,
    serverReason: spoken?.reason ?? null,
  });
});

watch(
  () => feedView.value.items.map((item) => item.id).join('|'),
  () => {
    const first = feedView.value.items[0];
    if (!first) {
      expandedId.value = null;
      return;
    }
    // Keep the top incident open so the Unified Inbox is useful at a glance.
    if (!expandedId.value || !feedView.value.items.some((item) => item.id === expandedId.value)) {
      expandedId.value = first.id;
    }
  },
  { immediate: true },
);

function focusSignal(signalId: string): void {
  shell.focusAttentionSidebar(signalId);
}

function toggleExpanded(signalId: string): void {
  expandedId.value = expandedId.value === signalId ? null : signalId;
}

function severityLabel(severity: string): string {
  return (severity || 'info').toUpperCase();
}
</script>

<template>
  <section class="operator-incident-feed" data-orb-obstacle="mission" aria-label="Unified inbox">
    <header class="operator-incident-feed__header" data-orb-field>
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
        data-orb-field
        :class="[
          `operator-incident-feed__item--${item.severity}`,
          { 'operator-incident-feed__item--expanded': expandedId === item.id },
        ]"
      >
        <div class="operator-incident-feed__row">
          <button
            type="button"
            class="operator-incident-feed__button"
            :aria-expanded="expandedId === item.id"
            @click="toggleExpanded(item.id)"
          >
            <span class="operator-incident-feed__item-title">
              {{ item.title }}
              <span
                class="operator-incident-feed__severity"
                :data-severity="item.severity"
              >
                {{ severityLabel(item.severity) }}
              </span>
              <span v-if="item.monitorSignal" class="operator-incident-feed__monitor-tag">
                Monitor
              </span>
            </span>
            <span class="operator-incident-feed__item-summary">
              {{ item.plainWhat || item.summary }}
            </span>
            <span class="operator-incident-feed__item-meta">
              {{ item.source === 'fleet' ? 'Fleet rollup' : 'Signal inbox' }}
              · {{ expandedId === item.id ? 'Hide detail' : 'Expand' }}
            </span>
          </button>
          <div v-if="item.source === 'signal'" class="operator-incident-feed__handoff-card">
            <HandoffToIdeButton
              :signal-id="item.id"
              :workspace-id="item.workspaceId"
              :title="item.title"
              :summary="item.summary"
              :meta="item.meta"
              compact
            />
          </div>
        </div>
        <div
          v-if="expandedId === item.id"
          class="operator-incident-feed__detail"
          role="region"
          :aria-label="`Incident detail for ${item.title}`"
        >
          <p class="operator-incident-feed__explain">
            <span class="operator-incident-feed__explain-label">What happened</span>
            {{ item.plainWhat || item.summary }}
          </p>
          <p class="operator-incident-feed__explain">
            <span class="operator-incident-feed__explain-label">What you should do</span>
            {{ item.plainYouDo }}
          </p>
          <p class="operator-incident-feed__explain">
            <span class="operator-incident-feed__explain-label">What the agent should do</span>
            {{ item.plainAgentDo }}
          </p>
          <p
            v-if="item.summary && item.summary !== item.plainWhat"
            class="operator-incident-feed__tech"
          >
            Tech note: {{ item.summary }}
          </p>
          <div class="operator-incident-feed__detail-actions">
            <button
              type="button"
              class="operator-incident-feed__focus"
              @click="focusSignal(item.id)"
            >
              Open in Attention
            </button>
          </div>
        </div>
      </li>
    </ul>
    <p v-else class="operator-incident-feed__empty">{{ feedView.emptyCopy }}</p>
    <p
      v-if="shell.handoffMutationError"
      class="operator-incident-feed__handoff-error"
      role="alert"
    >
      {{ shell.handoffMutationError }}
    </p>
  </section>
</template>
