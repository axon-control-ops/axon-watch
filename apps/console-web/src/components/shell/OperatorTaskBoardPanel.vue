<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue';

import {
  fetchWorkerSchedulerStatus,
  type WorkerSchedulerStatus,
} from '../../api/worker-scheduler-api';
import HudHoloPanelShell from '../../features/hud-holo/HudHoloPanelShell.vue';
import {
  taskBoardBucketToHoloTone,
  worstHudHoloTone,
  type HudHoloTone,
} from '../../features/hud-holo/hud-holo-tones';
import {
  buildOperatorTaskBoardView,
  type TaskBoardColumnId,
  type TaskBoardRow,
} from '../../lib/operator-task-board-view';
import { useShellStore } from '../../stores/shell';

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

const boardView = computed(() =>
  buildOperatorTaskBoardView(
    shell.workspaceTasksForCurrentWorkspace,
    shell.leadPlansForCurrentWorkspace,
  ),
);

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

onMounted(() => {
  void refreshScheduler();
});

function selectTask(taskId: string): void {
  selectedTaskId.value = selectedTaskId.value === taskId ? null : taskId;
}

function parseDependencies(): string[] {
  return dependenciesDraft.value
    .split(/[\s,]+/)
    .map((part) => part.trim())
    .filter(Boolean);
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
    dependencies: parseDependencies(),
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

function columnTone(columnId: TaskBoardColumnId): string {
  if (columnId === 'needs_attention') {
    return 'needs';
  }
  if (columnId === 'in_progress') {
    return 'live';
  }
  if (columnId === 'done') {
    return 'done';
  }
  return 'waiting';
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

      <div
        v-if="boardView.planGroups.length > 1"
        class="operator-task-board__plan-filter"
        data-orb-field
      >
        <button
          type="button"
          class="operator-task-board__plan-chip"
          :class="{ 'operator-task-board__plan-chip--active': planFilterId === 'all' }"
          @click="planFilterId = 'all'"
        >
          All plans
        </button>
        <button
          v-for="group in boardView.planGroups.filter((item) => item.planId)"
          :key="group.planId ?? 'none'"
          type="button"
          class="operator-task-board__plan-chip"
          :class="{ 'operator-task-board__plan-chip--active': planFilterId === group.planId }"
          @click="planFilterId = group.planId ?? 'all'"
        >
          {{ group.planGoal }}
          <span v-if="group.awaitingEngagement"> · engage</span>
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
            :disabled="shell.workspaceTasksMutating || shell.leadPlansMutating"
          />
        </label>
        <label class="operator-task-board__field operator-task-board__field--role">
          <span class="operator-task-board__field-label">Role</span>
          <select
            v-model="ownerRoleDraft"
            class="operator-task-board__select"
            :disabled="createAsLeadPlan || shell.workspaceTasksMutating"
          >
            <option v-for="role in roleOptions" :key="role.value" :value="role.value">
              {{ role.label }}
            </option>
          </select>
        </label>
        <label class="operator-task-board__field">
          <span class="operator-task-board__field-label">Risk</span>
          <select
            v-model="riskDraft"
            class="operator-task-board__select"
            :disabled="createAsLeadPlan || shell.workspaceTasksMutating"
          >
            <option value="low">Low</option>
            <option value="normal">Normal</option>
            <option value="high">High</option>
          </select>
        </label>
        <label class="operator-task-board__field">
          <span class="operator-task-board__field-label">Attempts</span>
          <input
            v-model.number="attemptBudgetDraft"
            class="operator-task-board__input"
            type="number"
            min="1"
            max="32"
            :disabled="createAsLeadPlan || shell.workspaceTasksMutating"
          />
        </label>
        <label class="operator-task-board__field operator-task-board__field--wide">
          <span class="operator-task-board__field-label">Done when</span>
          <input
            v-model="acceptanceDraft"
            class="operator-task-board__input"
            type="text"
            maxlength="240"
            placeholder="Optional acceptance criteria"
            :disabled="createAsLeadPlan || shell.workspaceTasksMutating"
          />
        </label>
        <label class="operator-task-board__field operator-task-board__field--wide">
          <span class="operator-task-board__field-label">Dependencies</span>
          <input
            v-model="dependenciesDraft"
            class="operator-task-board__input"
            type="text"
            maxlength="320"
            placeholder="Optional task ids, comma-separated"
            :disabled="createAsLeadPlan || shell.workspaceTasksMutating"
          />
        </label>
        <label class="operator-task-board__field operator-task-board__field--wide operator-task-board__check">
          <input v-model="createAsLeadPlan" type="checkbox" />
          <span>Create as Lead plan fan-out (multi-role)</span>
        </label>
        <button type="submit" class="operator-task-board__submit" :disabled="!canCreate">
          {{ createAsLeadPlan ? 'Fan out Lead plan' : 'Create task' }}
        </button>
      </form>

      <p
        v-if="shell.workspaceTasksError || shell.leadPlansError"
        class="operator-task-board__error"
        role="alert"
      >
        {{ shell.workspaceTasksError || shell.leadPlansError }}
      </p>

      <div class="operator-task-board__columns" data-orb-field>
        <section
          v-for="column in visibleColumns"
          :key="column.id"
          class="operator-task-board__column"
          :class="`operator-task-board__column--${columnTone(column.id)}`"
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
                @click="selectTask(row.taskId)"
              >
                <span class="operator-task-board__item-status">{{ row.status }}</span>
                <span class="operator-task-board__item-goal">{{ row.goal }}</span>
                <span class="operator-task-board__item-meta">
                  {{ row.ownerRole }} · attempts {{ row.attemptsLabel }}
                </span>
                <span
                  v-if="row.planGoal"
                  class="operator-task-board__chip operator-task-board__chip--plan"
                >
                  {{ row.planGoal }}
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
            </li>
          </ul>
          <p v-else class="operator-task-board__empty">{{ boardView.emptyCopy }}</p>
        </section>
      </div>

      <div class="operator-task-board__history-toggle" data-orb-field>
        <button type="button" class="operator-task-board__add" @click="showHistory = !showHistory">
          {{ showHistory ? 'Hide cancelled' : `Cancelled history (${boardView.counts.cancelled})` }}
        </button>
      </div>
      <ul v-if="showHistory && boardView.historyRows.length" class="operator-task-board__list">
        <li
          v-for="row in boardView.historyRows"
          :key="row.taskId"
          class="operator-task-board__item operator-task-board__item--cancelled"
        >
          <button type="button" class="operator-task-board__item-main" @click="selectTask(row.taskId)">
            <span class="operator-task-board__item-status">cancelled</span>
            <span class="operator-task-board__item-goal">{{ row.goal }}</span>
          </button>
        </li>
      </ul>

      <aside
        v-if="selectedRow"
        class="operator-task-board__drawer"
        data-orb-field
        aria-label="Selected task"
      >
        <header class="operator-task-board__drawer-head">
          <h4>{{ selectedRow.goal }}</h4>
          <button type="button" class="operator-task-board__cancel" @click="selectedTaskId = null">
            Close
          </button>
        </header>
        <p><strong>Status</strong> {{ selectedRow.status }}</p>
        <p><strong>Role</strong> {{ selectedRow.ownerRole }}</p>
        <p><strong>Risk</strong> {{ selectedRow.risk }}</p>
        <p><strong>Attempts</strong> {{ selectedRow.attemptsLabel }}</p>
        <p v-if="selectedRow.acceptance"><strong>Done when</strong> {{ selectedRow.acceptance }}</p>
        <p v-if="selectedRow.leaseHolder">
          <strong>Lease</strong> {{ selectedRow.leaseHolder }}
          <span v-if="selectedRow.leaseExpiresAt"> · expires {{ selectedRow.leaseExpiresAt }}</span>
        </p>
        <p v-if="selectedRow.terminalOutcome">
          <strong>Outcome</strong> {{ selectedRow.terminalOutcome }}
        </p>
        <p v-if="selectedRow.runId"><strong>Run</strong> {{ selectedRow.runId }}</p>
        <p v-if="selectedRow.planGoal">
          <strong>Lead plan</strong> {{ selectedRow.planGoal }}
          <span v-if="selectedRow.planKey"> · {{ selectedRow.planKey }}</span>
        </p>
        <p v-if="selectedRow.allowedPaths.length">
          <strong>Allowed paths</strong> {{ selectedRow.allowedPaths.join(', ') }}
        </p>
        <p v-if="selectedRow.exclusivePaths.length">
          <strong>Exclusive paths</strong> {{ selectedRow.exclusivePaths.join(', ') }}
        </p>
        <p v-if="selectedRow.dependencyChips.length">
          <strong>Dependencies</strong>
          {{
            selectedRow.dependencyChips
              .map((chip) => `${chip.goal} (${chip.status})`)
              .join(' · ')
          }}
        </p>
        <p><strong>Updated</strong> {{ selectedRow.updatedAt }}</p>
        <div class="operator-task-board__drawer-actions">
          <button
            v-if="selectedRow.runId"
            type="button"
            class="operator-task-board__submit"
            @click="openAssociatedRun(selectedRow)"
          >
            Open run
          </button>
          <button type="button" class="operator-task-board__submit" @click="openSpecialist(selectedRow)">
            Open specialist
          </button>
          <button
            v-if="selectedRow.canCancel"
            type="button"
            class="operator-task-board__cancel"
            :disabled="shell.workspaceTasksMutating"
            @click="cancelTask(selectedRow.taskId)"
          >
            Cancel task
          </button>
          <button
            v-if="selectedRow.canRetry"
            type="button"
            class="operator-task-board__submit"
            :disabled="shell.workspaceTasksMutating"
            @click="retryTask(selectedRow)"
          >
            Clone / retry
          </button>
          <button
            v-if="selectedRow.planId"
            type="button"
            class="operator-task-board__submit"
            :disabled="shell.leadPlansMutating"
            @click="reviewLeadPlan(selectedRow.planId)"
          >
            Review Lead plan
          </button>
        </div>
      </aside>
    </HudHoloPanelShell>
  </div>
</template>
