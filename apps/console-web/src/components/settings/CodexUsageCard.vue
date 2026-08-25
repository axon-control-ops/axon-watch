<script setup lang="ts">
import { computed } from 'vue';

import type { CodexUsageSnapshot } from '../../api/runtime-api';
import { codexUsageSummaryLine } from '../../lib/codex-usage-view';

const props = defineProps<{
  usage: CodexUsageSnapshot | null | undefined;
}>();

function formatBytes(value: number | null | undefined): string {
  if (value == null || Number.isNaN(Number(value))) {
    return '—';
  }
  const n = Number(value);
  if (n >= 1_000_000) {
    return `${(n / 1_000_000).toFixed(n >= 10_000_000 ? 0 : 1)}MB`;
  }
  if (n >= 1_000) {
    return `${(n / 1_000).toFixed(n >= 10_000 ? 0 : 1)}kB`;
  }
  return `${n}B`;
}

const summary = computed(() => codexUsageSummaryLine(props.usage));
const limitReached = computed(() => Boolean(props.usage?.limit_reached));
const stats = computed(() => [
  {
    id: 'events-24h',
    label: 'Events 24h',
    value: props.usage?.events_24h == null ? '—' : String(props.usage.events_24h),
    hint: 'Local Codex log events observed in the last 24 hours.',
  },
  {
    id: 'log-volume-24h',
    label: 'Log volume 24h',
    value: formatBytes(props.usage?.estimated_bytes_24h),
    hint: 'Estimated local log bytes; not a provider quota percentage.',
  },
  {
    id: 'latest-log',
    label: 'Latest log',
    value: props.usage?.latest_log_at?.trim() || '—',
    hint: props.usage?.source ? `Source: ${props.usage.source}` : 'No recent local log timestamp.',
  },
]);
</script>

<template>
  <section class="claude-usage-card" aria-label="Codex local usage telemetry">
    <header class="claude-usage-card__header">
      <div>
        <h3 class="claude-usage-card__title">Codex usage</h3>
        <p class="claude-usage-card__summary">{{ summary }}</p>
      </div>
      <span
        v-if="limitReached"
        class="claude-usage-card__badge claude-usage-card__badge--warn"
      >
        LIMIT
      </span>
    </header>

    <p class="claude-usage-card__note">
      Codex does not expose a live account quota endpoint here, so Axon-X shows
      local activity telemetry and limit signals from Codex logs.
    </p>

    <div class="claude-usage-card__stats">
      <div v-for="stat in stats" :key="stat.id" class="claude-usage-card__stat">
        <p class="claude-usage-card__stat-label">{{ stat.label }}</p>
        <p class="claude-usage-card__stat-value">{{ stat.value }}</p>
        <p class="claude-usage-card__stat-hint">{{ stat.hint }}</p>
      </div>
    </div>
  </section>
</template>
