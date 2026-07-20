<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';

import {
  buildConnectorRailRows,
  buildConnectorsRailSummaryLabel,
  buildConnectorsRailWatchOfflineBody,
  connectorsRailEmphasized,
  connectorsRailProbeListVisible,
} from '../../lib/connector-rail-view';
import { useShellStore } from '../../stores/shell';

const shell = useShellStore();
const reprobingConnectorId = ref<string | null>(null);

const rows = computed(() => buildConnectorRailRows(shell.connectorsItems));
const loading = computed(() => shell.connectorsLoadState === 'loading');
const watchConnected = computed(() => shell.runtimeSummary?.watch.connected ?? false);

const emphasized = computed(() =>
  connectorsRailEmphasized({
    watchConnected: watchConnected.value,
    summary: shell.connectorsSummary,
  }),
);
const summaryLabel = computed(() =>
  buildConnectorsRailSummaryLabel({
    loading: loading.value,
    watchConnected: watchConnected.value,
    summary: shell.connectorsSummary,
  }),
);

const probeListVisible = computed(() =>
  connectorsRailProbeListVisible({
    loading: loading.value,
    watchConnected: watchConnected.value,
    hasError: Boolean(shell.connectorsError),
  }),
);

const watchOfflineBody = buildConnectorsRailWatchOfflineBody();

function openLegacyFallback(url: string): void {
  window.open(url, '_blank', 'noopener,noreferrer');
}

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
      'connectors-rail-panel--watch-offline':
        !watchConnected && !loading && !shell.connectorsError,
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

    <p
      v-else-if="!watchConnected"
      class="connectors-rail-panel__status connectors-rail-panel__status--offline"
      role="status"
    >
      {{ watchOfflineBody }}
    </p>

    <ul v-else-if="probeListVisible && rows.length" class="connectors-rail-panel__list">
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
            :disabled="shell.connectorMutationPending"
            :title="`Reprobe ${row.label}`"
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
            :disabled="shell.connectorMutationPending"
            @click="shell.startCloudflareTunnel()"
          >
            Start tunnel
          </button>
          <button
            v-if="row.isTunnelConnector && row.tunnelRunning && row.tunnelManaged"
            type="button"
            class="connectors-rail-panel__action"
            :disabled="shell.connectorMutationPending"
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
          <button
            v-if="row.isLegacyFallback && row.fallbackUrl"
            type="button"
            class="connectors-rail-panel__action connectors-rail-panel__action--fallback"
            @click="openLegacyFallback(row.fallbackUrl)"
          >
            Open :7734 fallback
          </button>
        </div>
      </li>
    </ul>

    <p v-else class="connectors-rail-panel__status">No connectors configured.</p>

    <footer class="connectors-rail-panel__footer">
      <button
        type="button"
        class="connectors-rail-panel__refresh"
        :disabled="shell.connectorMutationPending"
        :title="shell.connectorMutationPending ? 'Refreshing watch summary' : 'Refresh watch summary'"
        :aria-label="shell.connectorMutationPending ? 'Refreshing watch summary' : 'Refresh watch summary'"
        @click="shell.refreshWatchSummary()"
      >
        {{ shell.connectorMutationPending ? 'Refreshing…' : 'Refresh summary' }}
      </button>
    </footer>
  </section>
</template>
