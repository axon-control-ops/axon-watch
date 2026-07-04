<script setup lang="ts">
import { computed } from 'vue';

import type { OperatorBriefing } from '../contracts/canonical';
import {
  briefingConnectivityLabels,
  briefingHasActions,
  briefingHasTopSignals,
  briefingIsEmpty,
  briefingPanelHeadline,
  type BriefingPanelLoadState,
} from '../lib/briefing-panel-view';

const props = defineProps<{
  briefing: OperatorBriefing | null;
  loadState: BriefingPanelLoadState;
  error: string | null;
  hero?: boolean;
}>();

const headline = computed(() => briefingPanelHeadline(props.briefing, props.loadState));
const showEmptyState = computed(
  () => props.loadState === 'loaded' && briefingIsEmpty(props.briefing),
);
const showActions = computed(
  () => props.loadState === 'loaded' && briefingHasActions(props.briefing),
);
const showTopSignals = computed(
  () => props.loadState === 'loaded' && briefingHasTopSignals(props.briefing),
);
const connectivityLabels = computed(() =>
  props.briefing ? briefingConnectivityLabels(props.briefing.connectivity) : [],
);
</script>

<template>
  <div class="briefing-panel" :class="{ 'briefing-panel--hero': hero }">
    <p class="briefing-panel__eyebrow">KAIRO Briefing</p>
    <strong class="briefing-panel__headline">{{ headline }}</strong>

    <p v-if="loadState === 'loading'" class="region-copy">Loading operator briefing…</p>
    <p v-else-if="loadState === 'error'" class="region-copy">{{ error }}</p>

    <div v-else-if="briefing" class="briefing-panel__section">
      <p class="briefing-panel__section-label">Connectivity</p>
      <div class="briefing-panel__chips">
        <span
          v-for="label in connectivityLabels"
          :key="label"
          class="briefing-panel__chip"
          :class="{
            'briefing-panel__chip--ok': label.endsWith('ready') || label.endsWith('connected'),
            'briefing-panel__chip--warn': label.includes('not ready') || label.includes('disconnected'),
          }"
        >
          {{ label }}
        </span>
      </div>
    </div>

    <p v-if="showEmptyState" class="region-copy">
      Systems nominal. No pending approvals, top signals, or recommended actions right now.
    </p>

    <div v-if="showTopSignals" class="briefing-panel__section">
      <p class="briefing-panel__section-label">Top signals</p>
      <ul class="briefing-panel__list">
        <li
          v-for="signal in briefing?.top_signals"
          :key="signal.signal_id"
          class="briefing-panel__item"
        >
          <span class="briefing-panel__item-title">{{ signal.title }}</span>
          <span class="region-copy">
            {{ signal.severity }} · {{ signal.status }} · workspace {{ signal.workspace_id }}
          </span>
        </li>
      </ul>
    </div>

    <div v-if="briefing && briefing.pending_approvals.count > 0" class="briefing-panel__section">
      <p class="briefing-panel__section-label">Pending approvals</p>
      <ul class="briefing-panel__list">
        <li
          v-for="item in briefing.pending_approvals.items"
          :key="item.approval_id"
          class="briefing-panel__item"
        >
          <span class="briefing-panel__item-title">{{ item.approval_id }}</span>
          <span class="region-copy">
            run {{ item.run_id }} · workspace {{ item.workspace_id }}
          </span>
        </li>
      </ul>
    </div>

    <div v-if="showActions" class="briefing-panel__section">
      <p class="briefing-panel__section-label">Next safe actions</p>
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

    <p v-if="briefing?.degraded.active" class="region-copy region-copy--degraded">
      Degraded state · {{ briefing.degraded.reasons.join(', ') }}
    </p>
  </div>
</template>
