<script setup lang="ts">
import { computed, ref, watch } from 'vue';

import {
  buildOperatorTaskBoardView,
  filterTaskBoardRows,
  type TaskBoardFilter,
} from '../../lib/operator-task-board-view';
import { useShellStore } from '../../stores/shell';

const shell = useShellStore();

const goalDraft = ref('');
const ownerRoleDraft = ref('backend');
const acceptanceDraft = ref('');
const showCreate = ref(false);
const filter = ref<TaskBoardFilter>('active');
const expandedId = ref<string | null>(null);

const boardView = computed(() =>
  buildOperatorTaskBoardView(shell.workspaceTasksForCurrentWorkspace),
);

watch(
  () => boardView.value.defaultFilter,
  (next) => {
    filter.value = next;
  },
  { immediate: true },
);

const visibleRows = computed(() =>
  filterTaskBoardRows(boardView.value.rows, filter.value),
);

const roleOptions = [
  { value: 'watcher', label: 'Watcher' },
  { value: 'frontend', label: 'Frontend' },
  { value: 'backend', label: 'Backend' },
  { value: 'integrations', label: 'Integrations' },
] as const;

const canCreate = computed(
  () =>
    Boolean(shell.currentWorkspace?.workspace_id) &&
    goalDraft.value.trim().length > 0 &&
    !shell.workspaceTasksMutating,
);

const chips = computed(() => {
  const c = boardView.value.counts;
  return [
    { id: 'active' as const, label: 'Active', count: c.open + c.leased },
    { id: 'done' as const, label: 'Done', count: c.completed },
    { id: 'failed' as const, label: 'Failed', count: c.failed },
    { id: 'cancelled' as const, label: 'Cancelled', count: c.cancelled },
  ];
});

function setFilter(next: TaskBoardFilter): void {
  filter.value = next;
  expandedId.value = null;
}

function toggleExpanded(taskId: string): void {
  expandedId.value = expandedId.value === taskId ? null : taskId;
}

async function submitTask(): Promise<void> {
  if (!canCreate.value) {
    return;
  }
  const created = await shell.createCurrentWorkspaceTask({
    goal: goalDraft.value.trim(),
    owner_role: ownerRoleDraft.value,
    acceptance_criteria: acceptanceDraft.value.trim(),
  });
  if (created) {
    goalDraft.value = '';
    acceptanceDraft.value = '';
    showCreate.value = false;
    filter.value = 'active';
  }
}

async function cancelTask(taskId: string): Promise<void> {
  await shell.cancelCurrentWorkspaceTask(taskId);
}
</script>

<template>
  <section
    class="operator-task-board operator-task-board-host"
    data-orb-obstacle="mission"
    aria-label="Task ledger"
  >
    <header class="operator-task-board__header" data-orb-field>
      <div class="operator-task-board__titles">
        <p class="operator-task-board__eyebrow">Specialist work queue</p>
        <h3 class="operator-task-board__title">Task board</h3>
        <p class="operator-task-board__purpose">{{ boardView.purpose }}</p>
      </div>
      <div class="operator-task-board__header-actions">
        <span class="operator-task-board__headline">{{ boardView.headline }}</span>
        <button
          type="button"
          class="operator-task-board__add"
          :aria-expanded="showCreate ? 'true' : 'false'"
          @click="showCreate = !showCreate"
        >
          {{ showCreate ? 'Hide form' : 'Add task' }}
        </button>
      </div>
    </header>

    <div class="operator-task-board__filters" role="tablist" aria-label="Task filters" data-orb-field>
      <button
        v-for="chip in chips"
        :key="chip.id"
        type="button"
        role="tab"
        class="operator-task-board__filter"
        :class="{
          'operator-task-board__filter--active': filter === chip.id,
          [`operator-task-board__filter--${chip.id}`]: true,
        }"
        :aria-selected="filter === chip.id"
        @click="setFilter(chip.id)"
      >
        <span class="operator-task-board__filter-count">{{ chip.count }}</span>
        {{ chip.label }}
      </button>
    </div>

    <form
      v-if="showCreate"
      class="operator-task-board__form"
      data-orb-field
      @submit.prevent="submitTask"
    >
      <label class="operator-task-board__field">
        <span class="operator-task-board__field-label">Goal</span>
        <input
          v-model="goalDraft"
          class="operator-task-board__input"
          type="text"
          maxlength="240"
          placeholder="What should this specialist finish?"
          :disabled="shell.workspaceTasksMutating"
        />
      </label>
      <label class="operator-task-board__field operator-task-board__field--role">
        <span class="operator-task-board__field-label">Role</span>
        <select
          v-model="ownerRoleDraft"
          class="operator-task-board__select"
          :disabled="shell.workspaceTasksMutating"
        >
          <option v-for="role in roleOptions" :key="role.value" :value="role.value">
            {{ role.label }}
          </option>
        </select>
      </label>
      <label class="operator-task-board__field operator-task-board__field--wide">
        <span class="operator-task-board__field-label">Done when</span>
        <input
          v-model="acceptanceDraft"
          class="operator-task-board__input"
          type="text"
          maxlength="240"
          placeholder="Optional acceptance criteria"
          :disabled="shell.workspaceTasksMutating"
        />
      </label>
      <button type="submit" class="operator-task-board__submit" :disabled="!canCreate">
        Create task
      </button>
    </form>

    <p v-if="shell.workspaceTasksError" class="operator-task-board__error" role="alert">
      {{ shell.workspaceTasksError }}
    </p>

    <ul v-if="visibleRows.length" class="operator-task-board__list">
      <li
        v-for="row in visibleRows"
        :key="row.taskId"
        class="operator-task-board__item"
        data-orb-field
        :class="[
          `operator-task-board__item--${row.bucket}`,
          { 'operator-task-board__item--expanded': expandedId === row.taskId },
        ]"
      >
        <button
          type="button"
          class="operator-task-board__item-main"
          @click="toggleExpanded(row.taskId)"
        >
          <span class="operator-task-board__item-status">{{ row.status }}</span>
          <span class="operator-task-board__item-goal">{{ row.goal }}</span>
          <span class="operator-task-board__item-meta">
            {{ row.ownerRole }} · attempts {{ row.attemptsLabel }}
          </span>
        </button>
        <button
          v-if="row.canCancel"
          type="button"
          class="operator-task-board__cancel"
          :disabled="shell.workspaceTasksMutating"
          @click="cancelTask(row.taskId)"
        >
          Cancel
        </button>
        <div v-if="expandedId === row.taskId" class="operator-task-board__detail">
          <p><strong>Role</strong> {{ row.ownerRole }}</p>
          <p v-if="row.acceptance"><strong>Done when</strong> {{ row.acceptance }}</p>
          <p v-if="row.runId"><strong>Run</strong> {{ row.runId }}</p>
          <p><strong>Meta</strong> {{ row.meta || '—' }}</p>
          <p><strong>Updated</strong> {{ row.updatedAt }}</p>
          <p class="operator-task-board__detail-hint">
            Cancelled ≠ failed. Failed needs a new task. Done means acceptance landed.
          </p>
        </div>
      </li>
    </ul>
    <p v-else class="operator-task-board__empty" data-orb-field>{{ boardView.emptyCopy }}</p>
  </section>
</template>
