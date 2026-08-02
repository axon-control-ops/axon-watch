<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue';

import { listWorkspaceHandoffs } from '../../../api/workspace-api';
import {
  incomingHandoffHeadline,
  incomingHandoffNextStep,
  mapWorkspaceHandoffRows,
  summarizeHandoffTask,
  type IncomingHandoffRow,
} from '../../../lib/workspace-handoff-board-view';
import { useShellStore } from '../../../stores/shell';

const emit = defineEmits<{
  selectTask: [taskId: string];
}>();

const shell = useShellStore();
const handoffRows = ref<IncomingHandoffRow[]>([]);
const openHandoffRows = computed(() => handoffRows.value.slice(0, 3));
const hiddenHandoffCount = computed(() => Math.max(0, handoffRows.value.length - 3));

async function refreshHandoffs(): Promise<void> {
  const workspaceId = shell.currentWorkspace?.workspace_id;
  if (!workspaceId) {
    handoffRows.value = [];
    return;
  }
  try {
    const snapshot = await listWorkspaceHandoffs(workspaceId);
    const taskStatusById: Record<string, string | undefined> = {};
    for (const task of shell.workspaceTasksForCurrentWorkspace) {
      taskStatusById[task.task_id] = task.status;
    }
    handoffRows.value = mapWorkspaceHandoffRows(snapshot.items, workspaceId, {
      taskStatusById,
    });
  } catch {
    handoffRows.value = [];
  }
}

function focusHandoffTask(row: IncomingHandoffRow): void {
  if (row.targetTaskId) {
    emit('selectTask', row.targetTaskId);
  }
}

onMounted(() => {
  void refreshHandoffs();
});

watch(
  () => [
    shell.currentWorkspace?.workspace_id ?? null,
    shell.workspaceTasksForCurrentWorkspace.map((task) => `${task.task_id}:${task.status}`).join('|'),
  ],
  () => {
    void refreshHandoffs();
  },
);
</script>

<template>
  <section
    v-if="openHandoffRows.length"
    class="operator-task-board__handoffs"
    data-orb-field
    aria-label="Tickets from other workspaces"
  >
    <header class="operator-task-board__handoffs-head">
      <div>
        <h4>From other workspaces</h4>
        <p class="operator-task-board__handoffs-help">
          Incoming = work sent here. Outgoing = you routed work out. Open the ticket to act.
        </p>
      </div>
      <span>{{ handoffRows.length }}</span>
    </header>
    <ul class="operator-task-board__handoff-list">
      <li
        v-for="row in openHandoffRows"
        :key="row.handoffId"
        class="operator-task-board__handoff-item"
        :class="`operator-task-board__handoff-item--${row.direction}`"
      >
        <button
          type="button"
          class="operator-task-board__handoff-button"
          @click="focusHandoffTask(row)"
        >
          <span class="operator-task-board__handoff-meta">
            <span class="operator-task-board__handoff-dir" :data-dir="row.direction">
              {{ row.direction === 'incoming' ? 'Incoming' : 'Outgoing' }}
            </span>
            {{ incomingHandoffHeadline(row) }}
          </span>
          <span class="operator-task-board__handoff-task">{{ summarizeHandoffTask(row.task) }}</span>
          <span class="operator-task-board__handoff-cta">{{ incomingHandoffNextStep(row) }} →</span>
        </button>
      </li>
    </ul>
    <p v-if="hiddenHandoffCount > 0" class="operator-task-board__handoffs-more">
      +{{ hiddenHandoffCount }} more — open a ticket above or filter Plans
    </p>
  </section>
</template>
