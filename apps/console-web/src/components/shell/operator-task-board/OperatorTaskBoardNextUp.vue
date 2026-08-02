<script setup lang="ts">
import { computed } from 'vue';

import type {
  OperatorTaskBoardView,
  TaskBoardRow,
} from '../../../lib/operator-task-board-view';

const props = defineProps<{
  boardView: OperatorTaskBoardView;
  autonomyMode: 'manual' | 'semi' | 'full';
  schedulerEffective: boolean;
  mutating: boolean;
}>();

const emit = defineEmits<{
  activate: [row: TaskBoardRow];
  openFleet: [];
}>();

const guidance = computed(() => {
  if (props.autonomyMode === 'full') {
    return props.schedulerEffective
      ? 'Full autonomy: safe queued work starts automatically. Critical or risky work still waits for your decision.'
      : 'Full autonomy is selected, but workers are paused. Resume Fleet or start a ticket manually.';
  }
  if (props.autonomyMode === 'semi') {
    return 'Semi-autonomous: Leads and watchers prepare this queue; you choose Start. Bound CI repair webhooks may still dispatch directly.';
  }
  return 'Manual / normal supervision: agents observe and queue work; you choose Start. Bound CI repair webhooks may still dispatch directly.';
});

const nextUpRow = computed(() => {
  const columns = props.boardView.columns;
  return (
    columns.find((column) => column.id === 'needs_attention')?.rows[0] ??
    columns
      .find((column) => column.id === 'waiting')
      ?.rows.find((row) => row.canStart) ??
    columns.find((column) => column.id === 'waiting')?.rows[0] ??
    columns.find((column) => column.id === 'in_progress')?.rows[0] ??
    columns
      .find((column) => column.id === 'done')
      ?.rows.find((row) => row.planAwaitingEngagement) ??
    null
  );
});
</script>

<template>
  <section class="operator-task-board__next-up" data-orb-field aria-label="Queue next step">
    <div class="operator-task-board__next-up-copy">
      <span class="operator-task-board__next-up-kicker">Your next step</span>
      <template v-if="nextUpRow">
        <strong>{{ nextUpRow.nextActionLabel }} · {{ nextUpRow.ownerRole }}</strong>
        <span>{{ nextUpRow.goal }}</span>
      </template>
      <span v-else>Nothing needs action in this workspace.</span>
      <p class="operator-task-board__next-up-mode">{{ guidance }}</p>
    </div>
    <div class="operator-task-board__next-up-actions">
      <button
        v-if="nextUpRow"
        type="button"
        class="operator-task-board__submit"
        :disabled="mutating"
        @click="emit('activate', nextUpRow)"
      >
        {{ nextUpRow.canStart ? 'Start next' : 'Open next step' }}
      </button>
      <button type="button" class="operator-task-board__scheduler-link" @click="emit('openFleet')">
        Change mode
      </button>
    </div>
  </section>
</template>
