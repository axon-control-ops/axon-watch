<script setup lang="ts">
import { computed, ref, watch } from 'vue';

import type {
  OperatorTaskBoardView,
  TaskBoardColumnId,
  TaskBoardRow,
} from '../../../lib/operator-task-board-view';

import { columnTone } from './operator-task-board-helpers';

/** Full-size cards in the Waiting column before "Show more". */
const WAITING_PREVIEW = 6;

const props = defineProps<{
  visibleColumns: OperatorTaskBoardView['columns'];
  boardView: OperatorTaskBoardView;
  selectedTaskId: string | null;
  showHistory: boolean;
  workspaceTasksMutating: boolean;
}>();

const emit = defineEmits<{
  selectTask: [taskId: string];
  startTask: [taskId: string];
  cancelTask: [taskId: string];
  dismissDone: [taskId: string];
  cancelAllWaiting: [];
  'update:showHistory': [value: boolean];
}>();

const waitingExpanded = ref(false);

watch(
  () => props.visibleColumns.find((column) => column.id === 'waiting')?.count ?? 0,
  (count) => {
    if (count <= WAITING_PREVIEW) {
      waitingExpanded.value = false;
    }
  },
);

const columnLayoutClass = computed(() => {
  const count = Math.min(props.visibleColumns.length, 4);
  const waiting = props.visibleColumns.find((column) => column.id === 'waiting');
  const heavyWaiting = Boolean(waiting && waiting.count >= 6 && count >= 2);
  return [
    `operator-task-board__columns--count-${count}`,
    { 'operator-task-board__columns--heavy-waiting': heavyWaiting },
  ];
});

function toneFor(columnId: TaskBoardColumnId): string {
  return columnTone(columnId);
}

function rowsForColumn(column: OperatorTaskBoardView['columns'][number]): TaskBoardRow[] {
  if (column.id !== 'waiting' || waitingExpanded.value) {
    return column.rows;
  }
  return column.rows.slice(0, WAITING_PREVIEW);
}

function hiddenWaitingCount(column: OperatorTaskBoardView['columns'][number]): number {
  if (column.id !== 'waiting') {
    return 0;
  }
  return Math.max(0, column.rows.length - WAITING_PREVIEW);
}
</script>

<template>
  <div
    class="operator-task-board__columns"
    :class="columnLayoutClass"
  >
    <section
      v-for="column in visibleColumns"
      :key="column.id"
      class="operator-task-board__column"
      :class="[
        `operator-task-board__column--${toneFor(column.id)}`,
        { 'operator-task-board__column--empty': column.count === 0 },
        { 'operator-task-board__column--queued': column.id === 'waiting' && column.count > 0 },
      ]"
    >
      <header class="operator-task-board__column-head">
        <h4>{{ column.label }}</h4>
        <div class="operator-task-board__column-head-meta">
          <span>{{ column.count }}</span>
          <button
            v-if="column.id === 'waiting' && column.count > 0"
            type="button"
            class="operator-task-board__column-clear"
            :disabled="workspaceTasksMutating"
            title="Clear waiting duplicates of completed work (and open twins) — keeps distinct follow-ups"
            @click="emit('cancelAllWaiting')"
          >
            Clear dupes
          </button>
        </div>
      </header>
      <ul
        v-if="column.rows.length"
        class="operator-task-board__list"
        :class="{
          'operator-task-board__list--queued': column.id === 'waiting',
          'operator-task-board__list--queued-expanded':
            column.id === 'waiting' && waitingExpanded,
        }"
      >
        <li
          v-for="row in rowsForColumn(column)"
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
            :title="row.goalFull"
            @click="emit('selectTask', row.taskId)"
          >
            <span class="operator-task-board__item-top">
              <span
                class="operator-task-board__item-status operator-task-board__item-action"
                :class="`operator-task-board__item-action--${row.nextActionTone}`"
              >
                {{ row.nextActionLabel }}
              </span>
              <span class="operator-task-board__item-role">{{ row.ownerRole }}</span>
            </span>
            <span
              v-if="row.planLabel"
              class="operator-task-board__item-plan"
              :title="row.planGoal ?? row.planLabel"
            >
              Lead · {{ row.planLabel }}
            </span>
            <span class="operator-task-board__item-goal">{{ row.goal }}</span>
            <span class="operator-task-board__item-next">{{ row.nextActionHint }}</span>
            <span class="operator-task-board__item-meta">
              {{ row.status }}
              <template v-if="row.bucket !== 'done'"> · attempts {{ row.attemptsLabel }}</template>
            </span>
            <span
              v-for="chip in row.dependencyChips.filter((item) => item.blocking).slice(0, 1)"
              :key="`${row.taskId}-${chip.taskId}`"
              class="operator-task-board__chip operator-task-board__chip--blocking"
            >
              blocked by {{ chip.goal }}
            </span>
          </button>
          <button
            v-if="row.canStart"
            type="button"
            class="operator-task-board__item-start"
            title="Start now — lease/dispatch specialist run into the IDE"
            aria-label="Start waiting task"
            :disabled="workspaceTasksMutating"
            @click.stop="emit('startTask', row.taskId)"
          >
            Start
          </button>
          <button
            v-if="row.canCancel"
            type="button"
            class="operator-task-board__item-cancel"
            title="Cancel queued task"
            aria-label="Cancel queued task"
            :disabled="workspaceTasksMutating"
            @click.stop="emit('cancelTask', row.taskId)"
          >
            ×
          </button>
          <button
            v-else-if="row.bucket === 'done'"
            type="button"
            class="operator-task-board__item-dismiss"
            title="Clear completed ticket from board"
            aria-label="Clear completed ticket from board"
            @click.stop="emit('dismissDone', row.taskId)"
          >
            ×
          </button>
        </li>
      </ul>
      <button
        v-if="column.id === 'waiting' && hiddenWaitingCount(column) > 0"
        type="button"
        class="operator-task-board__queue-more"
        @click="waitingExpanded = !waitingExpanded"
      >
        {{
          waitingExpanded
            ? 'Show fewer waiting'
            : `Show ${hiddenWaitingCount(column)} more waiting`
        }}
      </button>
      <p v-else-if="!column.rows.length" class="operator-task-board__empty">
        {{ boardView.emptyCopy }}
      </p>
    </section>
  </div>

  <div class="operator-task-board__history-toggle">
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
      <button
        type="button"
        class="operator-task-board__item-main"
        :title="row.goalFull"
        @click="emit('selectTask', row.taskId)"
      >
        <span class="operator-task-board__item-status">cancelled</span>
        <span class="operator-task-board__item-goal">{{ row.goal }}</span>
      </button>
    </li>
  </ul>
</template>
