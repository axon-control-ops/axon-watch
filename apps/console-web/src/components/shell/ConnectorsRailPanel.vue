<script setup lang="ts">
import { computed } from 'vue';

import { buildConnectorRailRows } from '../../lib/connector-rail-view';
import { useShellStore } from '../../stores/shell';

const shell = useShellStore();

const rows = computed(() => buildConnectorRailRows(shell.connectorsItems));
const summaryLabel = computed(() => {
  const summary = shell.connectorsSummary;
  if (!summary) {
    return 'Loading connectors…';
  }
  return `${summary.ok}/${summary.configured} ok · ${summary.required_unavailable} required down`;
});

function openLegacyFallback(url: string): void {
  window.open(url, '_blank', 'noopener,noreferrer');
}

function openTunnelUrl(url: string): void {
  window.open(url, '_blank', 'noopener,noreferrer');
}
</script>

<template>
  <section class="connectors-rail-panel" aria-label="Watch connectors">
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

    <ul v-else class="connectors-rail-panel__list">
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
            :disabled="shell.connectorMutationPending"
            @click="shell.reprobeConnector(row.connectorId)"
          >
            Reprobe
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
            v-if="row.isTunnelConnector && row.tunnelRunning"
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

    <footer class="connectors-rail-panel__footer">
      <button
        type="button"
        class="connectors-rail-panel__refresh"
        :disabled="shell.connectorMutationPending"
        @click="shell.refreshWatchSummary()"
      >
        {{ shell.connectorMutationPending ? 'Refreshing…' : 'Refresh summary' }}
      </button>
    </footer>
  </section>
</template>
