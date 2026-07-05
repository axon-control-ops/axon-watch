<script setup lang="ts">
import { computed } from 'vue';

import type { OperatorBriefing } from '../contracts/canonical';
import {
  briefingAdvise,
  briefingConnectivityLabels,
  briefingHasActions,
  briefingHasTopSignals,
  briefingIsEmpty,
  briefingNotice,
  briefingPanelHeadline,
  type BriefingPanelLoadState,
} from '../lib/briefing-panel-view';

const props = defineProps<{
  briefing: OperatorBriefing | null;
  loadState: BriefingPanelLoadState;
  error: string | null;
  hero?: boolean;
  summaryLine?: string;
}>();

const emit = defineEmits<{
  openChat: [];
}>();

const headline = computed(() => briefingPanelHeadline(props.briefing, props.loadState));
const heroNotice = computed(() => briefingNotice(props.briefing, props.loadState));
const heroAdvise = computed(() => briefingAdvise(props.briefing, props.loadState));
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
const personaEnabled = computed(
  () => props.briefing?.operator_presence?.settings?.operator_persona_enabled !== false,
);
const personaTitle = computed(() => (personaEnabled.value ? 'KAIRO' : 'Operator'));

const voiceLine = computed(() => {
  if (props.briefing?.operator_presence?.persona_voice_line) {
    return props.briefing.operator_presence.persona_voice_line;
  }
  if (props.loadState === 'loading') {
    return personaEnabled.value
      ? 'KAIRO: Standing by while briefing loads.'
      : 'Standing by while briefing loads.';
  }
  if (props.loadState === 'error') {
    return personaEnabled.value
      ? 'KAIRO: Briefing unavailable. Check control-plane connectivity.'
      : 'Briefing unavailable. Check control-plane connectivity.';
  }
  if (props.briefing?.pending_approvals.count) {
    return personaEnabled.value
      ? 'KAIRO: Approvals need your review before I can continue.'
      : 'Approvals need your review before execution can continue.';
  }
  if (props.briefing?.top_signals.length) {
    return personaEnabled.value
      ? 'KAIRO: Top signals need review. Tell me which workspace to focus.'
      : 'Top signals need review. Choose a workspace to focus.';
  }
  if (props.briefing?.degraded.active) {
    return personaEnabled.value
      ? 'KAIRO: Runtime is degraded. Review the status strip before continuing.'
      : 'Runtime is degraded. Review the status strip before continuing.';
  }
  return personaEnabled.value
    ? "KAIRO: I'm listening. Tell me what to focus on."
    : 'Ready. Tell me what to focus on.';
});
</script>

<template>
  <div
    class="briefing-panel briefing-panel--mockup"
    :class="{ 'briefing-panel--hero': hero }"
  >
    <template v-if="hero">
      <p v-if="summaryLine" class="briefing-panel__summary-line">{{ summaryLine }}</p>

      <div class="briefing-panel__hero-body">
        <div class="briefing-panel__reactor" aria-hidden="true">
          <span class="briefing-panel__reactor-grid" />
          <span class="briefing-panel__reactor-ring briefing-panel__reactor-ring--outer" />
          <span class="briefing-panel__reactor-ring briefing-panel__reactor-ring--mid" />
          <span class="briefing-panel__reactor-ring briefing-panel__reactor-ring--inner" />
          <span class="briefing-panel__reactor-core" />
          <span class="briefing-panel__reactor-sweep" />
        </div>

        <div class="briefing-panel__voice-copy">
          <p class="briefing-panel__kairo-title">{{ personaTitle }}</p>
          <p class="briefing-panel__section-label briefing-panel__section-label--hero">Notice</p>
          <p class="briefing-panel__kairo-subtitle">{{ heroNotice }}</p>
          <p class="briefing-panel__section-label briefing-panel__section-label--hero">Advise</p>
          <p class="briefing-panel__kairo-advise">{{ heroAdvise }}</p>
        </div>
      </div>
    </template>

    <template v-else>
      <div class="briefing-panel__presence">
        <div class="briefing-panel__avatar" aria-hidden="true">
          <span class="briefing-panel__avatar-core" />
          <span class="briefing-panel__avatar-ring" />
          <span class="briefing-panel__avatar-ring briefing-panel__avatar-ring--outer" />
          <span class="briefing-panel__avatar-ring briefing-panel__avatar-ring--pulse" />
        </div>
        <div class="briefing-panel__voice-copy">
          <p class="briefing-panel__voice-line">{{ voiceLine }}</p>
          <strong class="briefing-panel__headline">{{ headline }}</strong>
        </div>
      </div>

      <p v-if="loadState === 'loading'" class="region-copy">Loading operator briefing…</p>
      <p v-else-if="loadState === 'error'" class="region-copy region-copy--degraded">
        {{ error }}
      </p>

      <template v-else-if="briefing">
        <div class="briefing-panel__section">
          <p class="briefing-panel__section-label">Notice</p>
          <p class="briefing-panel__rhythm-copy">{{ heroNotice }}</p>
        </div>

        <div class="briefing-panel__section">
          <p class="briefing-panel__section-label">Advise</p>
          <p class="briefing-panel__rhythm-copy">{{ heroAdvise }}</p>
        </div>

        <div class="briefing-panel__section">
          <p class="briefing-panel__section-label">Connectivity</p>
          <div class="briefing-panel__chips">
            <span
              v-for="label in connectivityLabels"
              :key="label"
              class="briefing-panel__chip"
              :class="{
                'briefing-panel__chip--ok': label.endsWith('ready') || label.endsWith('connected'),
                'briefing-panel__chip--warn':
                  label.includes('not ready') || label.includes('disconnected'),
              }"
            >
              {{ label }}
            </span>
          </div>
        </div>
      </template>

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

      <button type="button" class="briefing-panel__cta" @click="emit('openChat')">
        <span class="briefing-panel__cta-icon" aria-hidden="true">◌</span>
        OPEN KAIRO CHAT
      </button>
    </template>
  </div>
</template>
