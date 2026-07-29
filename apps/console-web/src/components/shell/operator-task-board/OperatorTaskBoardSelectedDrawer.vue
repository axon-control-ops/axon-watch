<script setup lang="ts">
import type { TaskBoardRow } from '../../../lib/operator-task-board-view';

defineProps<{
  row: TaskBoardRow;
  workspaceTasksMutating: boolean;
  leadPlansMutating: boolean;
}>();

const emit = defineEmits<{
  close: [];
  openAssociatedRun: [row: TaskBoardRow];
  openSpecialist: [row: TaskBoardRow];
  cancelTask: [taskId: string];
  retryTask: [row: TaskBoardRow];
  reviewLeadPlan: [planId: string | null];
}>();
</script>

<template>
  <aside class="operator-task-board__drawer" data-orb-field aria-label="Selected task">
    <header class="operator-task-board__drawer-head">
      <h4>{{ row.goal }}</h4>
      <button type="button" class="operator-task-board__cancel" @click="emit('close')">
        Close
      </button>
    </header>
    <p><strong>Status</strong> {{ row.status }}</p>
    <p><strong>Role</strong> {{ row.ownerRole }}</p>
    <p><strong>Risk</strong> {{ row.risk }}</p>
    <p><strong>Attempts</strong> {{ row.attemptsLabel }}</p>
    <p v-if="row.acceptance"><strong>Done when</strong> {{ row.acceptance }}</p>
    <p v-if="row.leaseHolder">
      <strong>Lease</strong> {{ row.leaseHolder }}
      <span v-if="row.leaseExpiresAt"> · expires {{ row.leaseExpiresAt }}</span>
    </p>
    <p v-if="row.terminalOutcome">
      <strong>Outcome</strong> {{ row.terminalOutcome }}
    </p>
    <p v-if="row.runId"><strong>Run</strong> {{ row.runId }}</p>
    <p v-if="row.planGoal">
      <strong>Lead plan</strong> {{ row.planGoal }}
      <span v-if="row.planKey"> · {{ row.planKey }}</span>
    </p>
    <p v-if="row.allowedPaths.length">
      <strong>Allowed paths</strong> {{ row.allowedPaths.join(', ') }}
    </p>
    <p v-if="row.exclusivePaths.length">
      <strong>Exclusive paths</strong> {{ row.exclusivePaths.join(', ') }}
    </p>
    <p v-if="row.dependencyChips.length">
      <strong>Dependencies</strong>
      {{ row.dependencyChips.map((chip) => `${chip.goal} (${chip.status})`).join(' · ') }}
    </p>
    <p><strong>Updated</strong> {{ row.updatedAt }}</p>
    <div class="operator-task-board__drawer-actions">
      <button
        v-if="row.runId"
        type="button"
        class="operator-task-board__submit"
        @click="emit('openAssociatedRun', row)"
      >
        Open run
      </button>
      <button type="button" class="operator-task-board__submit" @click="emit('openSpecialist', row)">
        Open specialist
      </button>
      <button
        v-if="row.canCancel"
        type="button"
        class="operator-task-board__cancel"
        :disabled="workspaceTasksMutating"
        @click="emit('cancelTask', row.taskId)"
      >
        Cancel task
      </button>
      <button
        v-if="row.canRetry"
        type="button"
        class="operator-task-board__submit"
        :disabled="workspaceTasksMutating"
        @click="emit('retryTask', row)"
      >
        Clone / retry
      </button>
      <button
        v-if="row.planId"
        type="button"
        class="operator-task-board__submit"
        :disabled="leadPlansMutating"
        @click="emit('reviewLeadPlan', row.planId)"
      >
        Review Lead plan
      </button>
    </div>
  </aside>
</template>
