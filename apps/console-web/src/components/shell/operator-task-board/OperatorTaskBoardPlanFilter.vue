<script setup lang="ts">
import type { TaskBoardPlanGroup } from '../../../lib/operator-task-board-view';

defineProps<{
  planGroups: TaskBoardPlanGroup[];
  planFilterId: string | 'all';
  leadPlansMutating: boolean;
}>();

const emit = defineEmits<{
  'update:planFilterId': [value: string | 'all'];
  closeLeadPlan: [planId: string | null | undefined];
}>();
</script>

<template>
  <div
    v-if="planGroups.length > 1 || planGroups.some((group) => group.awaitingEngagement)"
    class="operator-task-board__plan-filter"
    data-orb-field
  >
    <button
      type="button"
      class="operator-task-board__plan-chip"
      :class="{ 'operator-task-board__plan-chip--active': planFilterId === 'all' }"
      @click="emit('update:planFilterId', 'all')"
    >
      All plans
    </button>
    <button
      v-for="group in planGroups.filter((item) => item.planId)"
      :key="group.planId ?? 'none'"
      type="button"
      class="operator-task-board__plan-chip"
      :class="{ 'operator-task-board__plan-chip--active': planFilterId === group.planId }"
      :title="group.planGoal"
      @click="emit('update:planFilterId', group.planId ?? 'all')"
    >
      {{ group.planLabel }}
      <span v-if="group.awaitingEngagement" class="operator-task-board__plan-chip-tag">
        engage
      </span>
    </button>
    <button
      v-for="group in planGroups.filter((item) => item.planId && item.awaitingEngagement)"
      :key="`close-${group.planId}`"
      type="button"
      class="operator-task-board__plan-chip operator-task-board__plan-chip--close"
      :disabled="leadPlansMutating"
      :title="`Close Lead plan: ${group.planGoal}`"
      @click.stop="emit('closeLeadPlan', group.planId)"
    >
      Close engage
    </button>
  </div>
</template>
