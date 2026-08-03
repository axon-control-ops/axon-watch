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

/** Keep the chip row short — Mission Control was a horizontal maze at 9+. */
const MAX_VISIBLE_PLANS = 4;

const plannedGroups = computed(() => props.planGroups.filter((item) => item.planId));

/** Engage-first so the row is a map, not a dump of every goal snippet. */
const rankedPlans = computed(() =>
  [...plannedGroups.value].sort((left, right) => {
    if (left.awaitingEngagement !== right.awaitingEngagement) {
      return left.awaitingEngagement ? -1 : 1;
    }
    return 0;
  }),
);

const visiblePlans = computed(() => rankedPlans.value.slice(0, MAX_VISIBLE_PLANS));
const hiddenPlanCount = computed(() =>
  Math.max(0, rankedPlans.value.length - MAX_VISIBLE_PLANS),
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

/** One Close CTA — not a Close chip per engage plan. */
const primaryClosePlan = computed(() => {
  if (props.planFilterId !== 'all') {
    return engageGroups.value.find((group) => group.planId === props.planFilterId) ?? null;
  }
  return engageGroups.value[0] ?? null;
});

const primaryReopenPlan = computed(() => {
  if (props.planFilterId !== 'all') {
    return reopenGroups.value.find((group) => group.planId === props.planFilterId) ?? null;
  }
  return reopenGroups.value[0] ?? null;
});

function selectEngagePlan(planId: string | null | undefined): void {
  emit('update:planFilterId', planId ?? 'all');
  emit('openVaxonReview', planId);
}
</script>

<template>
  <div v-if="showFilter" class="operator-task-board__plan-filter">
    <div class="operator-task-board__plan-filter-top">
      <p class="operator-task-board__plan-filter-label">Plans</p>
      <p class="operator-task-board__plan-filter-help">
        Filter the board. Engage opens Lead review in VAXON.
      </p>
    </div>
    <section
      v-for="group in engageGroups"
      :key="`decision-${group.planId}`"
      class="operator-task-board__lead-decision"
    >
      <p class="operator-task-board__lead-decision-eyebrow">Lead decision ready</p>
      <strong>{{ group.planLabel }}</strong>
      <p>{{ group.planGoal }}</p>
      <small>Review the verified Lead rollup before starting any follow-up work.</small>
      <div class="operator-task-board__lead-decision-actions">
        <button type="button" @click="selectEngagePlan(group.planId)">Review now</button>
        <button
          type="button"
          class="operator-task-board__lead-decision-complete"
          :disabled="leadPlansMutating"
          @click="emit('closeLeadPlan', group.planId)"
        >
          Mark review complete
        </button>
      </div>
    </section>
    <p class="operator-task-board__plan-filter-help">
      Review now opens the Lead rollup in VAXON. Mark review complete records that no further handoff is needed.
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
        All
        <span v-if="plannedGroups.length" class="operator-task-board__plan-chip-count">
          {{ plannedGroups.length }}
        </span>
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
          review now
        </span>
      </button>
      <span
        v-if="hiddenPlanCount > 0"
        class="operator-task-board__plan-more"
        :title="`${hiddenPlanCount} older plan(s) hidden — pick All or open a task`"
      >
        +{{ hiddenPlanCount }}
      </span>
      <button
        v-if="primaryClosePlan"
        type="button"
        class="operator-task-board__plan-chip operator-task-board__plan-chip--close"
        :disabled="leadPlansMutating"
        :title="`Close Lead review: ${primaryClosePlan.planGoal}`"
        @click.stop="emit('closeLeadPlan', primaryClosePlan.planId)"
      >
        Close review
        <span v-if="engageGroups.length > 1" class="operator-task-board__plan-chip-count">
          {{ engageGroups.length }}
        </span>
      </button>
      <button
        v-if="primaryReopenPlan"
        type="button"
        class="operator-task-board__plan-chip"
        :disabled="leadPlansMutating"
        :title="`Re-open Lead review for: ${primaryReopenPlan.planGoal}`"
        @click.stop="emit('reopenLeadPlan', primaryReopenPlan.planId)"
      >
        Re-open
      </button>
    </div>
    <label v-if="hiddenPlanCount > 0" class="operator-task-board__plan-select-label">
      <span class="sr-only">Jump to plan</span>
      <select
        class="operator-task-board__plan-select"
        :value="planFilterId"
        @change="
          emit(
            'update:planFilterId',
            (($event.target as HTMLSelectElement).value || 'all') as string | 'all',
          )
        "
      >
        <option value="all">All plans ({{ plannedGroups.length }})</option>
        <option
          v-for="group in rankedPlans"
          :key="group.planId ?? 'none'"
          :value="group.planId ?? 'all'"
        >
          {{ group.awaitingEngagement ? 'Engage · ' : '' }}{{ group.planLabel }}
        </option>
      </select>
    </label>
  </div>
</template>
