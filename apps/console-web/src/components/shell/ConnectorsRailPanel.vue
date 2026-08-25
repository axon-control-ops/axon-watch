<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';

import {
  buildConnectorRailRows,
  buildConnectorRailSummaryLabel,
  buildConnectorRailWatchOfflineStatus,
  connectorRailNeedsEmphasis,
} from '../../lib/connector-rail-view';
import { useShellStore } from '../../stores/shell';

const shell = useShellStore();
const reprobingConnectorId = ref<string | null>(null);

const rows = computed(() => buildConnectorRailRows(shell.connectorsItems));
const loading = computed(() => shell.connectorsLoadState === 'loading');
const watchConnected = computed(() => shell.runtimeSummary?.watch.connected ?? false);
const emphasized = computed(() =>
  connectorRailNeedsEmphasis({
    summary: shell.connectorsSummary,
    watchConnected: watchConnected.value,
  }),
);
const summaryLabel = computed(() =>
  buildConnectorRailSummaryLabel({
    loading: loading.value,
    summary: shell.connectorsSummary,
    watchConnected: watchConnected.value,
  }),
);
const watchOfflineStatus = computed(() =>
  buildConnectorRailWatchOfflineStatus(watchConnected.value),
);
const probeActionsPaused = computed(
  () => !watchConnected.value || shell.connectorMutationPending,
);

function openTunnelUrl(url: string): void {
  window.open(url, '_blank', 'noopener,noreferrer');
}

function reprobeLabel(connectorId: string): string {
  if (reprobingConnectorId.value === connectorId && shell.connectorMutationPending) {
    return 'Reprobing…';
  }

  return 'Reprobe';
}

async function handleReprobe(connectorId: string): Promise<void> {
  reprobingConnectorId.value = connectorId;

  try {
    await shell.reprobeConnector(connectorId);
  } finally {
    if (reprobingConnectorId.value === connectorId) {
      reprobingConnectorId.value = null;
    }
  }
}

onMounted(() => {
  if (shell.connectorsLoadState === 'idle') {
    void shell.loadConnectors();
  }
});
</script>

<template>
  <section
    id="watch-connectors-rail"
    class="connectors-rail-panel"
    :class="{
      'connectors-rail-panel--emphasized': emphasized,
      'connectors-rail-panel--watch-offline': Boolean(watchOfflineStatus) && !loading,
    }"
    aria-label="Watch connectors"
  >
    <header class="connectors-rail-panel__header">
      <div>
        <p class="connectors-rail-panel__eyebrow">Watch lane</p>
        <h3 class="connectors-rail-panel__title">Connectors</h3>
      </div>
      <span class="connectors-rail-panel__summary">{{ summaryLabel }}</span>
    </header>

    <p v-if="shell.connectorsError" class="connectors-rail-panel__error" role="alert">
      {{ shell.connectorsError }}
    </p>

    <p v-else-if="loading" class="connectors-rail-panel__status">Loading connectors…</p>

    <template v-else>
      <p
        v-if="watchOfflineStatus"
        class="connectors-rail-panel__status connectors-rail-panel__status--offline"
      >
        {{ watchOfflineStatus }}
      </p>

      <ul v-if="rows.length" class="connectors-rail-panel__list">
      <li
        v-for="row in rows"
        :key="row.connectorId"
        class="connectors-rail-panel__item"
        :class="`connectors-rail-panel__item--${row.tone}`"
      >
        <div class="connectors-rail-panel__item-copy">
          <span class="connectors-rail-panel__item-label">
            {{ row.label }}
            <span v-if="row.required" class="connectors-rail-panel__required">required</span>
          </span>
          <span class="connectors-rail-panel__item-status">{{ row.status }}</span>
          <span v-if="row.detail" class="connectors-rail-panel__item-detail">{{ row.detail }}</span>
        </div>
        <div class="connectors-rail-panel__item-actions">
          <button
            type="button"
            class="connectors-rail-panel__action"
            :class="{
              'connectors-rail-panel__action--pending':
                reprobingConnectorId === row.connectorId && shell.connectorMutationPending,
            }"
            :disabled="probeActionsPaused"
            :title="
              watchConnected
                ? `Reprobe ${row.label}`
                : 'Watch offline — reprobe paused until the watch reconnects'
            "
            :aria-label="`Reprobe ${row.label} connector`"
            :aria-busy="reprobingConnectorId === row.connectorId && shell.connectorMutationPending"
            @click="handleReprobe(row.connectorId)"
          >
            {{ reprobeLabel(row.connectorId) }}
          </button>
          <button
            v-if="row.isTunnelConnector && row.tunnelStartAllowed"
            type="button"
            class="connectors-rail-panel__action connectors-rail-panel__action--primary"
            :disabled="probeActionsPaused"
            @click="shell.startCloudflareTunnel()"
          >
            Start tunnel
          </button>
          <button
            v-if="row.isTunnelConnector && row.tunnelRunning && row.tunnelManaged"
            type="button"
            class="connectors-rail-panel__action"
            :disabled="probeActionsPaused"
            @click="shell.stopCloudflareTunnel()"
          >
            Stop tunnel
          </button>
          <button
            v-if="row.isTunnelConnector && row.tunnelUrl"
            type="button"
            class="connectors-rail-panel__action"
            @click="openTunnelUrl(row.tunnelUrl)"
          >
            Open tunnel URL
          </button>
        </div>
      </li>
      </ul>

      <p v-else class="connectors-rail-panel__status">No connectors configured.</p>
    </template>

    <footer class="connectors-rail-panel__footer">
      <button
        type="button"
        class="connectors-rail-panel__refresh"
        :disabled="probeActionsPaused"
        :title="
          shell.connectorMutationPending
            ? 'Refreshing watch summary'
            : watchConnected
              ? 'Refresh watch summary'
              : 'Watch offline — refresh paused until the watch reconnects'
        "
        :aria-label="
          shell.connectorMutationPending
            ? 'Refreshing watch summary'
            : watchConnected
              ? 'Refresh watch summary'
              : 'Watch offline — refresh paused until the watch reconnects'
        "
        @click="shell.refreshWatchSummary()"
      >
        {{ shell.connectorMutationPending ? 'Refreshing…' : 'Refresh summary' }}
      </button>
    </footer>
  </section>
</template>
