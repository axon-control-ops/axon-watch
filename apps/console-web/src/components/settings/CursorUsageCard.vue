<script setup lang="ts">
import { computed } from 'vue';

import type { CursorUsageSnapshot } from '../../api/runtime-api';
import {
  buildCursorUsageBars,
  cursorUsageSummaryLine,
} from '../../lib/cursor-usage-view';

const props = defineProps<{
  usage: CursorUsageSnapshot | null | undefined;
}>();

const bars = computed(() => buildCursorUsageBars(props.usage));
const summary = computed(() => cursorUsageSummaryLine(props.usage));
const totalPct = computed(() => {
  const total = bars.value.find((bar) => bar.id === 'total')?.percent;
  return total == null ? null : total;
});
</script>

<template>
  <section class="cursor-usage-card" aria-label="Cursor model quota usage">
    <header class="cursor-usage-card__header">
      <div>
        <h3 class="cursor-usage-card__title">Cursor usage</h3>
        <p class="cursor-usage-card__summary">{{ summary }}</p>
      </div>
      <span v-if="totalPct != null" class="cursor-usage-card__total">{{ totalPct }}%</span>
    </header>

    <div class="cursor-usage-card__bars">
      <div v-for="bar in bars" :key="bar.id" class="cursor-usage-card__row">
        <div class="cursor-usage-card__row-top">
          <span>{{ bar.label }}</span>
          <span>{{ bar.percent == null ? '—' : `${bar.percent}%` }}</span>
        </div>
        <div class="cursor-usage-card__track" :title="bar.hint">
          <div
            class="cursor-usage-card__fill"
            :class="{
              'cursor-usage-card__fill--warn': (bar.percent ?? 0) >= 95,
              'cursor-usage-card__fill--muted': bar.percent == null,
            }"
            :style="{ width: `${bar.percent ?? 0}%` }"
          />
        </div>
        <p class="cursor-usage-card__hint">{{ bar.hint }}</p>
      </div>
    </div>
  </section>
</template>
