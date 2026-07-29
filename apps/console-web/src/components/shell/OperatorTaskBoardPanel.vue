<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue';

import {
  fetchWorkerSchedulerStatus,
  type WorkerSchedulerStatus,
} from '../../api/worker-scheduler-api';
import { listWorkspaceHandoffs } from '../../api/workspace-api';
import HudHoloPanelShell from '../../features/hud-holo/HudHoloPanelShell.vue';
import {
  taskBoardBucketToHoloTone,
  worstHudHoloTone,
  type HudHoloTone,
} from '../../features/hud-holo/hud-holo-tones';
import {
  buildOperatorTaskBoardView,
  type TaskBoardRow,
} from '../../lib/operator-task-board-view';
import {
  incomingHandoffHeadline,
  mapWorkspaceHandoffRows,
  type IncomingHandoffRow,
} from '../../lib/workspace-handoff-board-view';
import { useShellStore } from '../../stores/shell';

import OperatorTaskBoardColumns from './operator-task-board/OperatorTaskBoardColumns.vue';
import OperatorTaskBoardCreateForm from './operator-task-board/OperatorTaskBoardCreateForm.vue';
import { parseDependencies } from './operator-task-board/operator-task-board-helpers';
import OperatorTaskBoardPlanFilter from './operator-task-board/OperatorTaskBoardPlanFilter.vue';
import OperatorTaskBoardSelectedDrawer from './operator-task-board/OperatorTaskBoardSelectedDrawer.vue';

const shell = useShellStore();

const goalDraft = ref('');
const ownerRoleDraft = ref('backend');
const acceptanceDraft = ref('');
const riskDraft = ref('normal');
const attemptBudgetDraft = ref(3);
const dependenciesDraft = ref('');
const createAsLeadPlan = ref(false);
const showCreate = ref(false);
const showHistory = ref(false);
const selectedTaskId = ref<string | null>(null);
const planFilterId = ref<string | 'all'>('all');
const scheduler = ref<WorkerSchedulerStatus | null>(null);
const schedulerError = ref<string | null>(null);
const handoffRows = ref<IncomingHandoffRow[]>([]);

const boardView = computed(() =>
  buildOperatorTaskBoardView(
    shell.workspaceTasksForCurrentWorkspace,
    shell.leadPlansForCurrentWorkspace,
  ),
);

const openHandoffRows = computed(() => handoffRows.value.slice(0, 6));

const roleOptions = computed(() => {
  const fromRoster = shell.companyEmployeesForCurrentWorkspace
    .map((employee) => ({
      value: String(employee.role || '').trim().toLowerCase(),
      label: employee.role_label || employee.name || String(employee.role || ''),
    }))
    .filter((row) => row.value);
  const unique = new Map(fromRoster.map((row) => [row.value, row]));
  if (!unique.size) {
    return [
      { value: 'watcher', label: 'Watcher' },
      { value: 'frontend', label: 'Frontend' },
      { value: 'backend', label: 'Backend' },
      { value: 'integrations', label: 'Integrations' },
    ];
  }
  return [...unique.values()];
});

watch(
  roleOptions,
  (options) => {
    if (!options.some((row) => row.value === ownerRoleDraft.value) && options[0]) {
      ownerRoleDraft.value = options[0].value;
    }
  },
  { immediate: true },
);

const selectedRow = computed(() =>
  boardView.value.rows.find((row) => row.taskId === selectedTaskId.value) ?? null,
);

const visibleColumns = computed(() => {
  if (planFilterId.value === 'all') {
    return boardView.value.columns;
  }
  return boardView.value.columns.map((column) => ({
    ...column,
    rows: column.rows.filter((row) => row.planId === planFilterId.value),
    count: column.rows.filter((row) => row.planId === planFilterId.value).length,
  }));
});

const holoTone = computed<HudHoloTone>(() => {
  const buckets = boardView.value.rows
    .filter((row) => row.bucket !== 'cancelled')
    .map((row) => taskBoardBucketToHoloTone(row.bucket));
  if (!buckets.length) {
    return 'nominal';
  }
  return worstHudHoloTone(buckets);
});

const canCreate = computed(
  () =>
    Boolean(shell.currentWorkspace?.workspace_id) &&
    goalDraft.value.trim().length > 0 &&
    !shell.workspaceTasksMutating &&
    !shell.leadPlansMutating,
);

const schedulerCopy = computed(() => {
  if (schedulerError.value) {
    return schedulerError.value;
  }
  if (!scheduler.value) {
    return null;
  }
  if (!scheduler.value.env_allowed) {
    return 'Workers blocked by environment';
  }
  if (scheduler.value.effective_enabled) {
    if (scheduler.value.executing_count <= 0) {
      return null;
    }
    return `${scheduler.value.executing_count} workers executing`;
  }
  return 'Workers paused';
});

const showSchedulerStrip = computed(() => Boolean(schedulerCopy.value));

async function refreshScheduler(): Promise<void> {
  try {
    scheduler.value = await fetchWorkerSchedulerStatus();
    schedulerError.value = null;
  } catch (error) {
    schedulerError.value =
      error instanceof Error ? error.message : 'Worker scheduler unavailable';
  }
}

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
    selectedTaskId.value = row.targetTaskId;
  }
}

onMounted(() => {
  void refreshScheduler();
  void refreshHandoffs();
});

watch(
  () => shell.currentWorkspace?.workspace_id ?? null,
  () => {
    void refreshHandoffs();
  },
);

function selectTask(taskId: string): void {
  selectedTaskId.value = selectedTaskId.value === taskId ? null : taskId;
}

async function closeLeadPlan(planId: string | null | undefined): Promise<void> {
  const cleaned = String(planId || '').trim();
  if (!cleaned) {
    return;
  }
  const closed = await shell.closeCurrentLeadPlanEngagement(cleaned, 'completed');
  if (closed && planFilterId.value === cleaned) {
    planFilterId.value = 'all';
  }
  await shell.loadOperatorBriefing({ background: true, light: true });
}

async function submitTask(): Promise<void> {
  if (!canCreate.value) {
    return;
  }
  if (createAsLeadPlan.value) {
    const created = await shell.fanOutCurrentWorkspaceLeadPlan({
      goal: goalDraft.value.trim(),
      mode: 'auto',
      create_runs: true,
    });
    if (created) {
      goalDraft.value = '';
      acceptanceDraft.value = '';
      dependenciesDraft.value = '';
      showCreate.value = false;
      await shell.loadWorkspaceTasks(shell.currentWorkspace?.workspace_id ?? '');
      await refreshScheduler();
    }
    return;
  }
  const created = await shell.createCurrentWorkspaceTask({
    goal: goalDraft.value.trim(),
    owner_role: ownerRoleDraft.value,
    acceptance_criteria: acceptanceDraft.value.trim(),
    risk: riskDraft.value,
    attempt_budget: attemptBudgetDraft.value,
    dependencies: parseDependencies(dependenciesDraft.value),
  });
  if (created) {
    goalDraft.value = '';
    acceptanceDraft.value = '';
    dependenciesDraft.value = '';
    showCreate.value = false;
    selectedTaskId.value = created.task_id;
  }
}

async function cancelTask(taskId: string): Promise<void> {
  await shell.cancelCurrentWorkspaceTask(taskId);
}

async function retryTask(row: TaskBoardRow): Promise<void> {
  const created = await shell.createCurrentWorkspaceTask({
    goal: row.goal,
    owner_role: row.ownerRole === 'unassigned' ? '' : row.ownerRole,
    acceptance_criteria: row.acceptance,
    risk: row.risk,
    attempt_budget: row.attemptBudget,
    dependencies: row.dependencyIds,
    allowed_paths: row.allowedPaths,
    exclusive_paths: row.exclusivePaths,
  });
  if (created) {
    selectedTaskId.value = created.task_id;
  }
}

async function openSpecialist(row: TaskBoardRow): Promise<void> {
  const employee = shell.companyEmployeesForCurrentWorkspace.find(
    (item) => String(item.role || '').trim().toLowerCase() === row.ownerRole.toLowerCase(),
  );
  if (!employee) {
    shell.setLayoutMode('ide');
    return;
  }
  await shell.openOrFocusEmployeeIdeThread(employee);
  shell.setLayoutMode('ide');
}

function openAssociatedRun(row: TaskBoardRow): void {
  if (!row.runId) {
    return;
  }
  const run = shell.runs.find((item) => item.run_id === row.runId);
  if (run?.employee_role) {
    const employee = shell.companyEmployeesForCurrentWorkspace.find(
      (item) =>
        String(item.role || '').trim().toLowerCase() ===
        String(run.employee_role || '').trim().toLowerCase(),
    );
    if (employee) {
      void shell.openOrFocusEmployeeIdeThread(employee);
    }
  } else {
    void openSpecialist(row);
  }
  shell.setLayoutMode('ide');
}

async function reviewLeadPlan(planId: string | null): Promise<void> {
  if (!planId) {
    return;
  }
  await shell.synthesizeCurrentLeadPlan(planId);
}

function openFleetControls(): void {
  shell.openOperatorPresenceSettingsPanel();
}
</script>

<template>
  <div
    id="operator-task-board"
    class="operator-task-board-host"
    data-orb-obstacle="mission"
  >
    <HudHoloPanelShell
      class="operator-task-board"
      label="task-board"
      variant="module"
      :tone="holoTone"
      aria-label="Task ledger"
    >
      <header class="operator-task-board__header" data-orb-field>
        <div class="operator-task-board__titles">
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

      <div v-if="showSchedulerStrip" class="operator-task-board__scheduler" data-orb-field>
        <p class="operator-task-board__scheduler-copy">{{ schedulerCopy }}</p>
        <button type="button" class="operator-task-board__scheduler-link" @click="openFleetControls">
          Fleet
        </button>
      </div>

      <section
        v-if="openHandoffRows.length"
        class="operator-task-board__handoffs"
        data-orb-field
        aria-label="Cross-workspace handoffs"
      >
        <header class="operator-task-board__handoffs-head">
          <h4>Cross-workspace tickets</h4>
          <span>{{ openHandoffRows.length }}</span>
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
                {{ incomingHandoffHeadline(row) }} · {{ row.status }}
              </span>
              <span class="operator-task-board__handoff-task">{{ row.task }}</span>
            </button>
          </li>
        </ul>
      </section>

      <OperatorTaskBoardPlanFilter
        :plan-groups="boardView.planGroups"
        :plan-filter-id="planFilterId"
        :lead-plans-mutating="shell.leadPlansMutating"
        @update:plan-filter-id="planFilterId = $event"
        @close-lead-plan="void closeLeadPlan($event)"
      />

      <OperatorTaskBoardCreateForm
        v-if="showCreate"
        v-model:goal-draft="goalDraft"
        v-model:owner-role-draft="ownerRoleDraft"
        v-model:acceptance-draft="acceptanceDraft"
        v-model:risk-draft="riskDraft"
        v-model:attempt-budget-draft="attemptBudgetDraft"
        v-model:dependencies-draft="dependenciesDraft"
        v-model:create-as-lead-plan="createAsLeadPlan"
        :role-options="roleOptions"
        :can-create="canCreate"
        :workspace-tasks-mutating="shell.workspaceTasksMutating"
        :lead-plans-mutating="shell.leadPlansMutating"
        @submit="void submitTask()"
      />

      <p
        v-if="shell.workspaceTasksError || shell.leadPlansError"
        class="operator-task-board__error"
        role="alert"
      >
        {{ shell.workspaceTasksError || shell.leadPlansError }}
      </p>

      <OperatorTaskBoardColumns
        :visible-columns="visibleColumns"
        :board-view="boardView"
        :selected-task-id="selectedTaskId"
        :show-history="showHistory"
        @select-task="selectTask"
        @update:show-history="showHistory = $event"
      />

      <OperatorTaskBoardSelectedDrawer
        v-if="selectedRow"
        :row="selectedRow"
        :workspace-tasks-mutating="shell.workspaceTasksMutating"
        :lead-plans-mutating="shell.leadPlansMutating"
        @close="selectedTaskId = null"
        @open-associated-run="openAssociatedRun"
        @open-specialist="void openSpecialist($event)"
        @cancel-task="void cancelTask($event)"
        @retry-task="void retryTask($event)"
        @review-lead-plan="void reviewLeadPlan($event)"
      />
    </HudHoloPanelShell>
  </div>
</template>
