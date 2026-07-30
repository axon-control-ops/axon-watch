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
  reopenLeadPlan: [planId: string | null | undefined];
  openVaxonReview: [planId: string | null | undefined];
}>();

const MAX_VISIBLE_PLANS = 10;

const plannedGroups = computed(() => props.planGroups.filter((item) => item.planId));
const visiblePlans = computed(() => plannedGroups.value.slice(0, MAX_VISIBLE_PLANS));
const hiddenPlanCount = computed(() =>
  Math.max(0, plannedGroups.value.length - MAX_VISIBLE_PLANS),
);
const engageGroups = computed(() =>
  plannedGroups.value.filter((item) => item.awaitingEngagement),
);
const reopenGroups = computed(() =>
  plannedGroups.value.filter(
    (item) =>
      !item.awaitingEngagement &&
      String(item.planStatus || '').toLowerCase() === 'completed' &&
      item.rows.some((row) => row.bucket === 'open' || row.bucket === 'leased'),
  ),
);
const showFilter = computed(
  () =>
    plannedGroups.value.length > 1 ||
    engageGroups.value.length > 0 ||
    reopenGroups.value.length > 0,
);

function selectEngagePlan(planId: string | null | undefined): void {
  emit('update:planFilterId', planId ?? 'all');
  emit('openVaxonReview', planId);
}
</script>

<template>
  <div v-if="showFilter" class="operator-task-board__plan-filter">
    <p class="operator-task-board__plan-filter-label">Plans</p>
    <p class="operator-task-board__plan-filter-help">
      Engage = Lead synthesis waiting in VAXON. Dismiss closes that review; Re-open brings the chip back.
    </p>
    <div class="operator-task-board__plan-tabs" role="tablist" aria-label="Lead plan filter">
      <button
        type="button"
        role="tab"
        class="operator-task-board__plan-chip"
        :class="{ 'operator-task-board__plan-chip--active': planFilterId === 'all' }"
        :aria-selected="planFilterId === 'all'"
        @click="emit('update:planFilterId', 'all')"
      >
        All plans
      </button>
      <button
        v-for="group in visiblePlans"
        :key="group.planId ?? 'none'"
        type="button"
        role="tab"
        class="operator-task-board__plan-chip"
        :class="{ 'operator-task-board__plan-chip--active': planFilterId === group.planId }"
        :aria-selected="planFilterId === group.planId"
        :title="
          group.awaitingEngagement
            ? `Open VAXON Lead review · ${group.planGoal}`
            : group.planGoal
        "
        @click="
          group.awaitingEngagement
            ? selectEngagePlan(group.planId)
            : emit('update:planFilterId', group.planId ?? 'all')
        "
      >
        <span class="operator-task-board__plan-chip-text">{{ group.planLabel }}</span>
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
        :title="`Dismiss Lead review in VAXON: ${group.planGoal}`"
        @click.stop="emit('closeLeadPlan', group.planId)"
      >
        Dismiss review · {{ group.planLabel }}
      </button>
      <button
        v-for="group in reopenGroups"
        :key="`reopen-${group.planId}`"
        type="button"
        class="operator-task-board__plan-chip"
        :disabled="leadPlansMutating"
        :title="`Re-open Lead review chip for: ${group.planGoal}`"
        @click.stop="emit('reopenLeadPlan', group.planId)"
      >
        Re-open review · {{ group.planLabel }}
      </button>
    </div>
  </div>
</template>
