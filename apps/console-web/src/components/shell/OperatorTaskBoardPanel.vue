<script setup lang="ts">
import { computed, ref } from 'vue';

import { buildOperatorTaskBoardView } from '../../lib/operator-task-board-view';
import { useShellStore } from '../../stores/shell';

const shell = useShellStore();

const goalDraft = ref('');
const ownerRoleDraft = ref('backend');
const acceptanceDraft = ref('');

const boardView = computed(() =>
  buildOperatorTaskBoardView(shell.workspaceTasksForCurrentWorkspace),
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
  }
}

async function cancelTask(taskId: string): Promise<void> {
  await shell.cancelCurrentWorkspaceTask(taskId);
}
</script>

<template>
  <section class="operator-task-board" aria-label="Task ledger">
    <header class="operator-task-board__header">
      <div>
        <p class="operator-task-board__eyebrow">Durable ledger</p>
        <h3 class="operator-task-board__title">Task board</h3>
      </div>
      <span class="operator-task-board__headline">{{ boardView.headline }}</span>
    </header>

    <div class="operator-task-board__counts" aria-label="Task counts">
      <span class="operator-task-board__count operator-task-board__count--open">
        {{ boardView.counts.open }} open
      </span>
      <span class="operator-task-board__count operator-task-board__count--leased">
        {{ boardView.counts.leased }} leased
      </span>
      <span class="operator-task-board__count operator-task-board__count--done">
        {{ boardView.counts.completed }} done
      </span>
      <span class="operator-task-board__count operator-task-board__count--failed">
        {{ boardView.counts.failed }} failed
      </span>
    </div>

    <form class="operator-task-board__form" @submit.prevent="submitTask">
      <label class="operator-task-board__field">
        <span class="operator-task-board__field-label">Goal</span>
        <input
          v-model="goalDraft"
          class="operator-task-board__input"
          type="text"
          maxlength="240"
          placeholder="Seed an open task for a specialist"
          :disabled="shell.workspaceTasksMutating"
        />
      </label>
      <label class="operator-task-board__field operator-task-board__field--role">
        <span class="operator-task-board__field-label">Owner role</span>
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
        <span class="operator-task-board__field-label">Acceptance</span>
        <input
          v-model="acceptanceDraft"
          class="operator-task-board__input"
          type="text"
          maxlength="240"
          placeholder="Optional acceptance criteria"
          :disabled="shell.workspaceTasksMutating"
        />
      </label>
      <button
        type="submit"
        class="operator-task-board__submit"
        :disabled="!canCreate"
      >
        Create task
      </button>
    </form>

    <p v-if="shell.workspaceTasksError" class="operator-task-board__error" role="alert">
      {{ shell.workspaceTasksError }}
    </p>

    <ul v-if="boardView.rows.length" class="operator-task-board__list">
      <li
        v-for="row in boardView.rows"
        :key="row.taskId"
        class="operator-task-board__item"
        :class="`operator-task-board__item--${row.bucket}`"
      >
        <div class="operator-task-board__item-main">
          <span class="operator-task-board__item-status">{{ row.status }}</span>
          <span class="operator-task-board__item-goal">{{ row.goal }}</span>
          <span class="operator-task-board__item-meta">
            {{ row.meta }} · attempts {{ row.attemptsLabel }}
          </span>
        </div>
        <button
          v-if="row.canCancel"
          type="button"
          class="operator-task-board__cancel"
          :disabled="shell.workspaceTasksMutating"
          @click="cancelTask(row.taskId)"
        >
          Cancel
        </button>
      </li>
    </ul>
    <p v-else class="operator-task-board__empty">{{ boardView.emptyCopy }}</p>
  </section>
</template>
