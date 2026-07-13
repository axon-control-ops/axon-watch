<script setup lang="ts">
import { computed } from 'vue';

import type { OperatorBriefing } from '../contracts/canonical';
import {
  briefingHasOpenLoops,
  buildBriefingOpenLoopRows,
  type OpenLoopRow,
} from '../lib/briefing-open-loops-view';
import { useShellStore } from '../stores/shell';

const props = defineProps<{
  briefing: OperatorBriefing | null;
  compact?: boolean;
}>();

const shell = useShellStore();

const rows = computed(() =>
  buildBriefingOpenLoopRows(props.briefing, { compact: Boolean(props.compact) }),
);
const visible = computed(() => rows.value.length > 0 || briefingHasOpenLoops(props.briefing));

function onActivate(row: OpenLoopRow): void {
  if (row.focusKind === 'attention') {
    shell.focusAttentionSidebar(row.signalId);
    return;
  }
  if (row.focusKind === 'command') {
    shell.focusCommandSeam();
    return;
  }
  shell.focusMissionControl();
}
</script>

<template>
  <div v-if="visible && rows.length" class="briefing-open-loops" aria-label="Open loops">
    <p class="briefing-open-loops__label">Open loops</p>
    <ul class="briefing-open-loops__list">
      <li v-for="row in rows" :key="row.id" class="briefing-open-loops__item">
        <button type="button" class="briefing-open-loops__button" @click="onActivate(row)">
          <span class="briefing-open-loops__title">{{ row.label }}</span>
          <span v-if="row.meta" class="briefing-open-loops__meta">{{ row.meta }}</span>
        </button>
      </li>
    </ul>
  </div>
</template>
