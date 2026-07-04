<script setup lang="ts">
import { computed } from 'vue';

import type { OperatorBriefing } from '../contracts/canonical';
import {
  briefingHasActions,
  briefingIsEmpty,
  briefingPanelHeadline,
  type BriefingPanelLoadState,
} from '../lib/briefing-panel-view';

const props = defineProps<{
  briefing: OperatorBriefing | null;
  loadState: BriefingPanelLoadState;
  error: string | null;
}>();

const headline = computed(() => briefingPanelHeadline(props.briefing, props.loadState));
const showEmptyState = computed(
  () => props.loadState === 'loaded' && briefingIsEmpty(props.briefing),
);
const showActions = computed(
  () => props.loadState === 'loaded' && briefingHasActions(props.briefing),
);
</script>

<template>
  <div class="placeholder-card briefing-panel">
    <p class="placeholder-card__label">OperatorBriefing</p>
    <strong>{{ headline }}</strong>

    <p v-if="loadState === 'error'" class="region-copy">{{ error }}</p>

    <p v-else-if="showEmptyState" class="region-copy">
      No pending approvals or next safe actions in the current briefing projection.
    </p>

    <div v-if="briefing && briefing.pending_approvals.count > 0" class="briefing-panel__section">
      <p class="briefing-panel__section-label">pending_approvals</p>
      <ul class="briefing-panel__list">
        <li
          v-for="item in briefing.pending_approvals.items"
          :key="item.approval_id"
          class="briefing-panel__item"
        >
          <span class="briefing-panel__item-title">{{ item.approval_id }}</span>
          <span class="region-copy">
            run_id={{ item.run_id }} · workspace_id={{ item.workspace_id }}
          </span>
        </li>
      </ul>
    </div>

    <div v-if="showActions" class="briefing-panel__section">
      <p class="briefing-panel__section-label">next_safe_actions</p>
      <ul class="briefing-panel__list">
        <li
          v-for="action in briefing?.next_safe_actions"
          :key="action.action_id"
          class="briefing-panel__item"
        >
          <span class="briefing-panel__item-title">{{ action.title }}</span>
          <span class="region-copy">{{ action.detail }}</span>
          <span class="briefing-panel__kind">{{ action.kind }}</span>
        </li>
      </ul>
    </div>

    <p v-if="briefing?.degraded.active" class="region-copy">
      degraded={{ briefing.degraded.active }} · {{ briefing.degraded.reasons.join(', ') }}
    </p>
  </div>
</template>
