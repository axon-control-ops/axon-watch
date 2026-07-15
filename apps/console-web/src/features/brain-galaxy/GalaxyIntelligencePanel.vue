<script setup lang="ts">
import { computed } from 'vue';

import { projectGalaxyIntelligence } from './galaxy-intelligence-projector';
import type { GalaxyPresencePhase } from './galaxy-presence-state';
import { useShellStore } from '../../stores/shell';

const props = defineProps<{
  presencePhase: GalaxyPresencePhase;
  routingReceipt?: string | null;
}>();

const shell = useShellStore();

const view = computed(() =>
  projectGalaxyIntelligence({
    briefing: shell.operatorBriefing,
    briefingLoadState: shell.briefingLoadState,
    primaryActiveRun: shell.primaryActiveRun,
    presencePhase: props.presencePhase,
    workspaceLabel: shell.currentWorkspace?.display_name ?? shell.currentWorkspace?.workspace_id ?? null,
    routingReceipt: props.routingReceipt ?? null,
  }),
);
</script>

<template>
  <aside class="galaxy-intelligence-panel" aria-label="VAXON intelligence">
    <header class="galaxy-intelligence-panel__header">
      <p class="galaxy-intelligence-panel__eyebrow">Intelligence</p>
      <span
        class="galaxy-intelligence-panel__phase"
        :data-phase="view.presencePhase"
      >
        {{ view.presencePhase.replace('_', ' ') }}
      </span>
    </header>

    <p class="galaxy-intelligence-panel__headline">{{ view.headline }}</p>
    <p class="galaxy-intelligence-panel__notice">{{ view.notice }}</p>
    <p class="galaxy-intelligence-panel__advise">{{ view.advise }}</p>

    <div class="galaxy-intelligence-panel__chips" aria-label="Live signals">
      <span
        v-if="view.approvalCount > 0"
        class="galaxy-intelligence-panel__chip galaxy-intelligence-panel__chip--critical"
      >
        {{ view.approvalCount }} approvals
      </span>
      <span
        v-if="view.criticalSignals > 0"
        class="galaxy-intelligence-panel__chip galaxy-intelligence-panel__chip--critical"
      >
        {{ view.criticalSignals }} critical
      </span>
      <span
        v-if="view.highSignals > 0"
        class="galaxy-intelligence-panel__chip galaxy-intelligence-panel__chip--attention"
      >
        {{ view.highSignals }} high
      </span>
      <span
        v-if="view.runPhaseLabel"
        class="galaxy-intelligence-panel__chip galaxy-intelligence-panel__chip--info"
      >
        Run · {{ view.runPhaseLabel }}
      </span>
      <span
        v-if="view.workspaceLabel"
        class="galaxy-intelligence-panel__chip"
      >
        {{ view.workspaceLabel }}
      </span>
    </div>

    <section v-if="view.topSignalTitles.length" class="galaxy-intelligence-panel__section">
      <p class="galaxy-intelligence-panel__section-label">Critical signals</p>
      <ul>
        <li v-for="title in view.topSignalTitles" :key="title">{{ title }}</li>
      </ul>
    </section>

    <section v-if="view.safeActions.length" class="galaxy-intelligence-panel__section">
      <p class="galaxy-intelligence-panel__section-label">
        Suggested actions · guidance only
      </p>
      <ul>
        <li v-for="action in view.safeActions" :key="`${action.kind}:${action.action_id}`">
          {{ action.title }}
        </li>
      </ul>
    </section>

    <section v-if="view.degradedReasons.length" class="galaxy-intelligence-panel__section">
      <p class="galaxy-intelligence-panel__section-label">Degraded</p>
      <ul>
        <li v-for="reason in view.degradedReasons" :key="reason">{{ reason }}</li>
      </ul>
    </section>

    <section
      v-if="view.connectivityChips.length"
      class="galaxy-intelligence-panel__section galaxy-intelligence-panel__section--conn"
    >
      <p class="galaxy-intelligence-panel__section-label">Connectivity</p>
      <div class="galaxy-intelligence-panel__chips">
        <span
          v-for="chip in view.connectivityChips"
          :key="chip.id"
          class="galaxy-intelligence-panel__chip"
          :class="`galaxy-intelligence-panel__chip--${chip.tone}`"
        >
          {{ chip.label }}
        </span>
      </div>
    </section>

    <p v-if="view.routingReceipt" class="galaxy-intelligence-panel__receipt">
      {{ view.routingReceipt }}
    </p>
  </aside>
</template>
