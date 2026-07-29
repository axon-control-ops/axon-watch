<script setup lang="ts">
import type {
  OperatorTaskBoardView,
  TaskBoardColumnId,
} from '../../../lib/operator-task-board-view';

import { columnTone } from './operator-task-board-helpers';

defineProps<{
  visibleColumns: OperatorTaskBoardView['columns'];
  boardView: OperatorTaskBoardView;
  selectedTaskId: string | null;
  showHistory: boolean;
  workspaceTasksMutating: boolean;
}>();

const emit = defineEmits<{
  selectTask: [taskId: string];
  cancelTask: [taskId: string];
  'update:showHistory': [value: boolean];
}>();

function toneFor(columnId: TaskBoardColumnId): string {
  return columnTone(columnId);
}
</script>

<template>
  <div class="operator-task-board__columns" data-orb-field>
    <section
      v-for="column in visibleColumns"
      :key="column.id"
      class="operator-task-board__column"
      :class="`operator-task-board__column--${toneFor(column.id)}`"
    >
      <header class="operator-task-board__column-head">
        <h4>{{ column.label }}</h4>
        <span>{{ column.count }}</span>
      </header>
      <ul v-if="column.rows.length" class="operator-task-board__list">
        <li
          v-for="row in column.rows"
          :key="row.taskId"
          class="operator-task-board__item"
          :class="[
            `operator-task-board__item--${row.bucket}`,
            { 'operator-task-board__item--selected': selectedTaskId === row.taskId },
            { 'operator-task-board__item--blocked': row.blockedByOpenDeps },
          ]"
        >
          <button
            type="button"
            class="operator-task-board__item-main"
            @click="emit('selectTask', row.taskId)"
          >
            <span class="operator-task-board__item-status">{{ row.status }}</span>
            <span class="operator-task-board__item-goal">{{ row.goal }}</span>
            <span class="operator-task-board__item-meta">
              {{ row.ownerRole }} · attempts {{ row.attemptsLabel }}
            </span>
            <span
              v-if="row.planLabel"
              class="operator-task-board__chip operator-task-board__chip--plan"
              :title="row.planGoal || undefined"
            >
              {{ row.planLabel }}
            </span>
            <span
              v-for="chip in row.dependencyChips"
              :key="`${row.taskId}-${chip.taskId}`"
              class="operator-task-board__chip"
              :class="{ 'operator-task-board__chip--blocking': chip.blocking }"
            >
              {{ chip.blocking ? 'blocked by' : 'after' }} {{ chip.goal }}
            </span>
          </button>
          <button
            v-if="row.canCancel"
            type="button"
            class="operator-task-board__item-cancel"
            title="Cancel queued task"
            :disabled="workspaceTasksMutating"
            @click.stop="emit('cancelTask', row.taskId)"
          >
            Cancel
          </button>
        </li>
      </ul>
      <p v-else class="operator-task-board__empty">{{ boardView.emptyCopy }}</p>
    </section>
  </div>

  <div class="operator-task-board__history-toggle" data-orb-field>
    <button
      type="button"
      class="operator-task-board__add"
      @click="emit('update:showHistory', !showHistory)"
    >
      {{ showHistory ? 'Hide cancelled' : `Cancelled history (${boardView.counts.cancelled})` }}
    </button>
  </div>
  <ul v-if="showHistory && boardView.historyRows.length" class="operator-task-board__list">
    <li
      v-for="row in boardView.historyRows"
      :key="row.taskId"
      class="operator-task-board__item operator-task-board__item--cancelled"
    >
      <button type="button" class="operator-task-board__item-main" @click="emit('selectTask', row.taskId)">
        <span class="operator-task-board__item-status">cancelled</span>
        <span class="operator-task-board__item-goal">{{ row.goal }}</span>
      </button>
    </li>
  </ul>
</template>
