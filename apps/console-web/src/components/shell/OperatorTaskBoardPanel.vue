<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from 'vue';

import { openLeadReviewOverlay, leadReviewOverlayError } from '../../features/lead-review/lead-review-overlay-state';
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
import { resolveTaskBoardCardActivation } from '../../lib/operator-task-board-activate';
import { buildOperatorTaskBoardView, type TaskBoardRow } from '../../lib/operator-task-board-view';
import {
  dismissDoneTaskId,
  dismissDoneTaskIds,
  loadDismissedDoneTaskIds,
} from '../../lib/task-board-dismissed-done';
import { useShellStore } from '../../stores/shell';

import OperatorTaskBoardColumns from './operator-task-board/OperatorTaskBoardColumns.vue';
import OperatorTaskBoardCreateForm from './operator-task-board/OperatorTaskBoardCreateForm.vue';
import OperatorTaskBoardHandoffs from './operator-task-board/OperatorTaskBoardHandoffs.vue';
import OperatorTaskBoardNextUp from './operator-task-board/OperatorTaskBoardNextUp.vue';
import OperatorTaskBoardPlanFilter from './operator-task-board/OperatorTaskBoardPlanFilter.vue';
import OperatorTaskBoardSelectedDrawer from './operator-task-board/OperatorTaskBoardSelectedDrawer.vue';
import {
  openTaskBoardAssociatedRun,
  submitTaskBoardCreate,
} from './operator-task-board/task-board-panel-actions';
import { confirmCancelAllWaiting, confirmClearDuplicateWaiting } from './operator-task-board/task-board-waiting-clear';
import { useOperatorTaskBoardRouting } from './operator-task-board/use-operator-task-board-routing';

const shell = useShellStore();
const { openSpecialist, startTaskAndOpenOwner } = useOperatorTaskBoardRouting();
const goalDraft = ref('');
const ownerRoleDraft = ref('backend');
const acceptanceDraft = ref('');
const riskDraft = ref('normal');
const attemptBudgetDraft = ref(3);
const dependenciesDraft = ref('');
const createAsLeadPlan = ref(false);
// Mission Control is VAXON's orchestration surface. Keep the task composer
// visible so an operator can delegate or fan out work without dropping into
// the compact conversational reply seam.
const showCreate = ref(true);
const showHistory = ref(false);
const selectedTaskId = ref<string | null>(null);
const selectedDrawerEl = ref<HTMLElement | null>(null);
const planFilterId = ref<string | 'all'>('all');
const scheduler = ref<WorkerSchedulerStatus | null>(null);
const schedulerError = ref<string | null>(null);
const dismissedDoneIds = ref<Set<string>>(loadDismissedDoneTaskIds());

const boardView = computed(() => {
  const runPhaseByTaskId: Record<string, string> = {};
  for (const run of shell.runs) {
    const taskId = String(run.task_id || '').trim();
    const phase = String(run.phase || '').trim();
    if (taskId && phase) {
      runPhaseByTaskId[taskId] = phase;
    }
    const runId = String(run.run_id || '').trim();
    if (runId && phase) {
      runPhaseByTaskId[runId] = phase;
    }
  }
  return buildOperatorTaskBoardView(
    shell.workspaceTasksForCurrentWorkspace,
    shell.leadPlansForCurrentWorkspace,
    runPhaseByTaskId,
  );
});

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
  const source =
    planFilterId.value === 'all'
      ? boardView.value.columns
      : boardView.value.columns.map((column) => ({
          ...column,
          rows: column.rows.filter((row) => row.planId === planFilterId.value),
          count: column.rows.filter((row) => row.planId === planFilterId.value).length,
        }));

  const withDismissals = source.map((column) => {
    if (column.id !== 'done') {
      return column;
    }
    const rows = column.rows.filter((row) => !dismissedDoneIds.value.has(row.taskId));
    return {
      ...column,
      rows,
      count: rows.length,
    };
  });

  const active = withDismissals.filter((column) => column.count > 0);
  return active.length > 0 ? active : withDismissals;
});

const doneVisibleCount = computed(
  () => visibleColumns.value.find((column) => column.id === 'done')?.count ?? 0,
);


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

async function revealSelectedDrawer(): Promise<void> {
  await nextTick();
  selectedDrawerEl.value?.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
}

/** Card click: run the labeled next action (not a silent select below the fold). */
function activateTaskCard(taskId: string): void {
  const row = boardView.value.rows.find((item) => item.taskId === taskId);
  if (!row) {
    selectTask(taskId);
    void revealSelectedDrawer();
    return;
  }
  const action = resolveTaskBoardCardActivation(row);
  if (action.kind === 'focus_blocker') {
    selectedTaskId.value = action.blockerTaskId;
    void revealSelectedDrawer();
    return;
  }
  selectedTaskId.value = taskId;
  if (action.kind === 'open_failure' || action.kind === 'open_run') {
    openAssociatedRun(action.row);
  } else if (action.kind === 'open_specialist') {
    void openSpecialist(action.row);
    shell.setLayoutMode('ide');
  } else if (action.kind === 'open_vaxon_review') {
    void openVaxonReview(action.planId);
  }
  void revealSelectedDrawer();
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

async function reopenLeadPlan(planId: string | null | undefined): Promise<void> {
  const cleaned = String(planId || '').trim();
  if (!cleaned) {
    return;
  }
  const opened = await shell.reopenCurrentLeadPlanEngagement(cleaned);
  if (opened) {
    planFilterId.value = cleaned;
    shell.focusLiveOperations();
  }
  await shell.loadOperatorBriefing({ background: true, light: true });
}

async function openVaxonReview(planId?: string | null): Promise<void> {
  const cleaned = String(planId || '').trim();
  planFilterId.value = cleaned || planFilterId.value;
  shell.focusLiveOperations();
  if (!cleaned) {
    return;
  }
  const opened = await openLeadReviewOverlay(cleaned);
  if (!opened) {
    shell.commandMutationError =
      leadReviewOverlayError.value
      || 'Could not open the Lead rollup in Live operations.';
  }
}

const selectedPlanAwaitingEngagement = computed(() => {
  const planId = selectedRow.value?.planId;
  if (!planId) {
    return false;
  }
  return boardView.value.planGroups.some(
    (group) => group.planId === planId && group.awaitingEngagement,
  );
});

async function startTask(taskId: string): Promise<void> {
  await startTaskAndOpenOwner(
    taskId, refreshScheduler, (startedTaskId) => (selectedTaskId.value = startedTaskId),
  );
}

async function submitTask(): Promise<void> {
  const result = await submitTaskBoardCreate({
    shell,
    createAsLeadPlan: createAsLeadPlan.value,
    goal: goalDraft.value,
    ownerRole: ownerRoleDraft.value,
    acceptance: acceptanceDraft.value,
    risk: riskDraft.value,
    attemptBudget: attemptBudgetDraft.value,
    dependenciesDraft: dependenciesDraft.value,
    canCreate: canCreate.value,
    refreshScheduler,
  });
  if (!result.cleared) {
    return;
  }
  goalDraft.value = '';
  acceptanceDraft.value = '';
  dependenciesDraft.value = '';
  if (result.selectedTaskId) {
    selectedTaskId.value = result.selectedTaskId;
  }
}

async function cancelTask(taskId: string): Promise<void> {
  await shell.cancelCurrentWorkspaceTask(taskId);
}

function dismissDoneTask(taskId: string): void {
  dismissedDoneIds.value = dismissDoneTaskId(taskId, dismissedDoneIds.value);
  if (selectedTaskId.value === taskId) {
    selectedTaskId.value = null;
  }
}

function clearVisibleDone(): void {
  const doneIds =
    boardView.value.columns
      .find((column) => column.id === 'done')
      ?.rows.map((row) => row.taskId) ?? [];
  if (!doneIds.length) {
    return;
  }
  dismissedDoneIds.value = dismissDoneTaskIds(doneIds, dismissedDoneIds.value);
  if (selectedTaskId.value && doneIds.includes(selectedTaskId.value)) {
    selectedTaskId.value = null;
  }
}

async function cancelAllWaiting(): Promise<void> {
  if (await confirmCancelAllWaiting({
    waitingCount: boardView.value.counts.waiting, mutating: shell.workspaceTasksMutating,
    cancelAll: () => shell.cancelWaitingWorkspaceTasks(),
  })) { selectedTaskId.value = null; await refreshScheduler(); }
}

async function clearDuplicateWaiting(): Promise<void> {
  if (await confirmClearDuplicateWaiting({
    mutating: shell.workspaceTasksMutating,
    clearDuplicates: () => shell.clearDuplicateWaitingWorkspaceTasks(),
  })) { selectedTaskId.value = null; await refreshScheduler(); }
}

async function retryTask(row: TaskBoardRow): Promise<void> {
  const created = await shell.createCurrentWorkspaceTask({
    goal: row.goalFull || row.goal,
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

function openAssociatedRun(row: TaskBoardRow): void {
  openTaskBoardAssociatedRun({ shell, row, openSpecialist });
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

function activateNextUp(row: TaskBoardRow): void {
  if (row.canStart) {
    void startTask(row.taskId);
    return;
  }
  activateTaskCard(row.taskId);
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
          <div class="operator-task-board__header-buttons">
            <button
              v-if="doneVisibleCount > 0"
              type="button"
              class="operator-task-board__clear-done"
              title="Hide completed tickets from this board (session only)"
              @click="clearVisibleDone()"
            >
              Clear done ({{ doneVisibleCount }})
            </button>
            <button
              v-if="boardView.counts.waiting > 0"
              type="button"
              class="operator-task-board__cancel-waiting"
              :disabled="shell.workspaceTasksMutating"
              title="Cancel every open/waiting task so Leads are not buried"
              @click="void cancelAllWaiting()"
            >
              Cancel all waiting ({{ boardView.counts.waiting }})
            </button>
            <button
              type="button"
              class="operator-task-board__add"
              :aria-expanded="showCreate ? 'true' : 'false'"
              @click="showCreate = !showCreate"
            >
              {{ showCreate ? 'Hide work composer' : 'Show work composer' }}
            </button>
          </div>
        </div>
      </header>

      <div v-if="showSchedulerStrip" class="operator-task-board__scheduler" data-orb-field>
        <p class="operator-task-board__scheduler-copy">{{ schedulerCopy }}</p>
        <button type="button" class="operator-task-board__scheduler-link" @click="openFleetControls">
          Fleet
        </button>
      </div>

      <OperatorTaskBoardNextUp
        :board-view="boardView"
        :autonomy-mode="shell.operatorPresenceSettings.autonomy_mode"
        :scheduler-effective="scheduler?.effective_enabled ?? false"
        :mutating="shell.workspaceTasksMutating"
        @activate="activateNextUp"
        @open-fleet="openFleetControls"
      />

      <OperatorTaskBoardHandoffs @select-task="selectedTaskId = $event" />

      <OperatorTaskBoardPlanFilter
        :plan-groups="boardView.planGroups"
        :plan-filter-id="planFilterId"
        :lead-plans-mutating="shell.leadPlansMutating"
        @update:plan-filter-id="planFilterId = $event"
        @close-lead-plan="void closeLeadPlan($event)"
        @reopen-lead-plan="void reopenLeadPlan($event)"
        @open-vaxon-review="openVaxonReview($event)"
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
        :workspace-tasks-mutating="shell.workspaceTasksMutating"
        @select-task="activateTaskCard"
        @start-task="void startTask($event)"
        @cancel-task="void cancelTask($event)"
        @dismiss-done="dismissDoneTask"
        @clear-duplicate-waiting="void clearDuplicateWaiting()"
        @update:show-history="showHistory = $event"
      />

      <div
        v-if="selectedRow"
        ref="selectedDrawerEl"
        class="operator-task-board__drawer-anchor"
      >
        <OperatorTaskBoardSelectedDrawer
          :row="selectedRow"
          :workspace-tasks-mutating="shell.workspaceTasksMutating"
          :lead-plans-mutating="shell.leadPlansMutating"
          :plan-awaiting-engagement="selectedPlanAwaitingEngagement"
          @close="selectedTaskId = null"
          @start-task="void startTask($event)"
          @open-associated-run="openAssociatedRun"
          @open-specialist="void openSpecialist($event)"
          @open-vaxon-review="openVaxonReview(selectedRow.planId)"
          @cancel-task="void cancelTask($event)"
          @retry-task="void retryTask($event)"
          @review-lead-plan="void reviewLeadPlan($event)"
        />
      </div>
    </HudHoloPanelShell>
  </div>
</template>
