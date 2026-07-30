<script setup lang="ts">
import type { TaskBoardRow } from '../../../lib/operator-task-board-view';

const props = defineProps<{
  row: TaskBoardRow;
  workspaceTasksMutating: boolean;
  leadPlansMutating: boolean;
  planAwaitingEngagement?: boolean;
}>();

const emit = defineEmits<{
  close: [];
  startTask: [taskId: string];
  openAssociatedRun: [row: TaskBoardRow];
  openSpecialist: [row: TaskBoardRow];
  openVaxonReview: [];
  cancelTask: [taskId: string];
  retryTask: [row: TaskBoardRow];
  reviewLeadPlan: [planId: string | null];
}>();

function nextStepCopy(): string {
  if (props.row.canStart) {
    return 'Start leases this ticket to the specialist and queues the run. Full Autonomy dispatches workers; or open the specialist to drive it in IDE.';
  }
  if (props.row.blockedByOpenDeps) {
    return 'Blocked by unfinished dependencies — it stays in Waiting until those complete (or you cancel).';
  }
  if (props.row.bucket === 'leased') {
    return 'Already leased / in progress. Open the run or specialist to follow the work.';
  }
  if (props.planAwaitingEngagement) {
    return 'Lead Engage is open in VAXON — review the synthesis there, or dismiss the review chip when done.';
  }
  return 'Select an action below.';
}
</script>

<template>
  <aside class="operator-task-board__drawer" aria-label="Selected task">
    <header class="operator-task-board__drawer-head">
      <h4>{{ row.goalFull || row.goal }}</h4>
      <button type="button" class="operator-task-board__cancel" @click="emit('close')">
        Close
      </button>
    </header>
    <p class="operator-task-board__drawer-hint">{{ nextStepCopy() }}</p>
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
        v-if="row.canStart"
        type="button"
        class="operator-task-board__submit"
        :disabled="workspaceTasksMutating"
        @click="emit('startTask', row.taskId)"
      >
        Start now
      </button>
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
        v-if="planAwaitingEngagement"
        type="button"
        class="operator-task-board__submit"
        @click="emit('openVaxonReview')"
      >
        Open VAXON review
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
