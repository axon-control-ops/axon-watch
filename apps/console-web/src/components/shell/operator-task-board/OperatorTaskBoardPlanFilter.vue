<script setup lang="ts">
import { computed } from 'vue';

import type { TaskBoardPlanGroup } from '../../../lib/operator-task-board-view';

const props = defineProps<{
  planGroups: TaskBoardPlanGroup[];
  planFilterId: string | 'all';
  leadPlansMutating: boolean;
}>();

const emit = defineEmits<{
  'update:planFilterId': [value: string | 'all'];
  closeLeadPlan: [planId: string | null | undefined];
}>();

const MAX_VISIBLE_PLANS = 6;

const plannedGroups = computed(() => props.planGroups.filter((item) => item.planId));
const visiblePlans = computed(() => plannedGroups.value.slice(0, MAX_VISIBLE_PLANS));
const hiddenPlanCount = computed(() =>
  Math.max(0, plannedGroups.value.length - MAX_VISIBLE_PLANS),
);
const engageGroups = computed(() =>
  plannedGroups.value.filter((item) => item.awaitingEngagement),
);
const showFilter = computed(
  () => plannedGroups.value.length > 1 || engageGroups.value.length > 0,
);
</script>

<template>
  <div v-if="showFilter" class="operator-task-board__plan-filter" data-orb-field>
    <button
      type="button"
      class="operator-task-board__plan-chip"
      :class="{ 'operator-task-board__plan-chip--active': planFilterId === 'all' }"
      @click="emit('update:planFilterId', 'all')"
    >
      All plans
    </button>
    <button
      v-for="group in visiblePlans"
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
    <span
      v-if="hiddenPlanCount > 0"
      class="operator-task-board__plan-more"
      :title="`${hiddenPlanCount} older plan(s) hidden — filter via All or open a task`"
    >
      +{{ hiddenPlanCount }} more
    </span>
    <button
      v-for="group in engageGroups"
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
