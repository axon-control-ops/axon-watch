<script setup lang="ts">
import { computed } from 'vue';

import type { ClaudeUsageSnapshot } from '../../api/runtime-api';
import { buildClaudeUsageStats, claudeUsageSummaryLine } from '../../lib/claude-usage-view';

const props = defineProps<{
  usage: ClaudeUsageSnapshot | null | undefined;
}>();

const stats = computed(() => buildClaudeUsageStats(props.usage));
const summary = computed(() => claudeUsageSummaryLine(props.usage));
const limitReached = computed(() => Boolean(props.usage?.limit_reached));
</script>

<template>
  <section class="claude-usage-card" aria-label="Claude Code usage">
    <header class="claude-usage-card__header">
      <div>
        <h3 class="claude-usage-card__title">Claude usage</h3>
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
      Anthropic has no personal quota API like Cursor's dashboard, so these are
      local Claude Code telemetry stats plus a live limit-reached signal — not
      a live account-quota percentage.
    </p>

    <div class="claude-usage-card__stats">
      <div v-for="stat in stats" :key="stat.id" class="claude-usage-card__stat">
        <p class="claude-usage-card__stat-label">{{ stat.label }}</p>
        <p class="claude-usage-card__stat-value">{{ stat.value }}</p>
        <p v-if="stat.hint" class="claude-usage-card__stat-hint">{{ stat.hint }}</p>
      </div>
    </div>
  </section>
</template>
