<script setup lang="ts">
import { computed, ref } from 'vue';

import { useOrbFieldReactiveHost } from '../../composables/useOrbFieldReactiveHost';
import HudHoloPanelShell from '../../features/hud-holo/HudHoloPanelShell.vue';
import {
  taskBoardBucketToHoloTone,
  type HudHoloSignal,
  type HudHoloTone,
} from '../../features/hud-holo/hud-holo-tones';
import { buildOperatorTaskBoardView } from '../../lib/operator-task-board-view';
import { useShellStore } from '../../stores/shell';

const shell = useShellStore();
const rootEl = ref<HTMLElement | null>(null);

useOrbFieldReactiveHost({ root: rootEl });

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

const holoTone = computed<HudHoloTone>(() => {
  if (boardView.value.counts.failed > 0) {
    return 'critical';
  }
  if (boardView.value.counts.open > 0 || boardView.value.counts.leased > 0) {
    return 'attention';
  }
  return 'nominal';
});

const holoSignals = computed<HudHoloSignal[]>(() => {
  const { counts } = boardView.value;
  const total = Math.max(1, counts.total);
  return [
    {
      id: 'open',
      tone: taskBoardBucketToHoloTone('open'),
      weight: counts.open / total,
      selected: counts.open > 0 && counts.failed === 0,
    },
    {
      id: 'leased',
      tone: taskBoardBucketToHoloTone('leased'),
      weight: counts.leased / total,
      selected: counts.leased > 0,
    },
    {
      id: 'done',
      tone: taskBoardBucketToHoloTone('done'),
      weight: counts.completed / total,
    },
    {
      id: 'failed',
      tone: taskBoardBucketToHoloTone('failed'),
      weight: counts.failed / total,
      selected: counts.failed > 0,
    },
  ].filter((signal) => (signal.weight ?? 0) > 0);
});

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
  <div
    ref="rootEl"
    class="operator-task-board-host"
    :class="{ 'operator-task-board-host--orb-live': shell.voiceOrbDragging }"
  >
    <HudHoloPanelShell
      class="operator-task-board"
      label="task-board"
      variant="module"
      :tone="holoTone"
      :signals="holoSignals"
      aria-label="Task ledger"
    >
      <header class="operator-task-board__header" data-orb-field>
        <div>
          <p class="operator-task-board__eyebrow">Durable ledger</p>
          <h3 class="operator-task-board__title">Task board</h3>
        </div>
        <span class="operator-task-board__headline">{{ boardView.headline }}</span>
      </header>

      <div class="operator-task-board__counts" aria-label="Task counts" data-orb-field>
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

      <form class="operator-task-board__form" data-orb-field @submit.prevent="submitTask">
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
          data-orb-field
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
      <p v-else class="operator-task-board__empty" data-orb-field>{{ boardView.emptyCopy }}</p>
    </HudHoloPanelShell>
  </div>
</template>
