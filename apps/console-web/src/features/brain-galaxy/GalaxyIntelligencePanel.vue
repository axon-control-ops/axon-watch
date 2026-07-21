<script setup lang="ts">
import { computed, ref } from 'vue';

import type { BriefingAction } from '../../contracts/canonical';
import {
  briefingActionCtaLabel,
  executeBriefingAction,
} from '../../lib/briefing-action-executor';
import {
  dismissEmployeeSpecialtyRoute,
  undoEmployeeSpecialtyRoute,
} from '../../lib/apply-employee-specialty-route';
import { teammateRouteNotice } from '../../lib/teammate-route-notice';
import HostCapabilityPanel from '../host-context/HostCapabilityPanel.vue';
import { projectGalaxyIntelligence } from './galaxy-intelligence-projector';
import type { GalaxyPresencePhase } from './galaxy-presence-state';
import { formatSpecialtyRouteChip } from './specialty-dispatch-filament';
import { useShellStore } from '../../stores/shell';

const props = defineProps<{
  presencePhase: GalaxyPresencePhase;
  routingReceipt?: string | null;
}>();

const shell = useShellStore();
const actionPendingId = ref<string | null>(null);
const hostContextOpen = ref(false);

const specialtyChip = computed(() => {
  const notice = teammateRouteNotice.value;
  return notice ? formatSpecialtyRouteChip(notice) : null;
});

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

async function onActivateAction(action: BriefingAction): Promise<void> {
  if (actionPendingId.value || shell.handoffMutationState === 'submitting') {
    return;
  }
  actionPendingId.value = action.action_id;
  try {
    await executeBriefingAction(shell, shell.operatorBriefing, action);
  } finally {
    actionPendingId.value = null;
  }
}

async function undoSpecialtyRoute(): Promise<void> {
  await undoEmployeeSpecialtyRoute(shell, teammateRouteNotice.value);
}

function dismissSpecialtyRoute(): void {
  dismissEmployeeSpecialtyRoute();
}
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
    <p v-if="view.notice" class="galaxy-intelligence-panel__notice">{{ view.notice }}</p>
    <p v-if="view.advise" class="galaxy-intelligence-panel__advise">{{ view.advise }}</p>

    <div
      v-if="specialtyChip"
      class="galaxy-intelligence-panel__specialty-route"
      role="status"
    >
      <p class="galaxy-intelligence-panel__specialty-route-copy">{{ specialtyChip }}</p>
      <div class="galaxy-intelligence-panel__specialty-route-actions">
        <button type="button" @click="undoSpecialtyRoute">Undo</button>
        <button type="button" aria-label="Dismiss specialty route" @click="dismissSpecialtyRoute">
          Dismiss
        </button>
      </div>
    </div>

    <div
      v-if="(shell.operatorBriefing?.due_reminders?.length ?? 0) > 0"
      class="galaxy-intelligence-panel__reminders"
      aria-label="Due reminders"
    >
      <p
        v-for="item in shell.operatorBriefing?.due_reminders?.slice(0, 2) ?? []"
        :key="item.memory_id"
        class="galaxy-intelligence-panel__reminder"
      >
        {{ item.title }}
      </p>
    </div>

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
      <p class="galaxy-intelligence-panel__section-label">Suggested actions</p>
      <ul class="galaxy-intelligence-panel__action-list">
        <li
          v-for="action in view.safeActions"
          :key="`${action.kind}:${action.action_id}`"
          class="galaxy-intelligence-panel__action-item"
        >
          <button
            type="button"
            class="galaxy-intelligence-panel__action-button"
            :disabled="
              actionPendingId === action.action_id || shell.handoffMutationState === 'submitting'
            "
            @click="onActivateAction(action)"
          >
            <span class="galaxy-intelligence-panel__action-title">{{ action.title }}</span>
            <span class="galaxy-intelligence-panel__action-detail">{{ action.detail }}</span>
            <span class="galaxy-intelligence-panel__action-cta">
              {{
                actionPendingId === action.action_id || shell.handoffMutationState === 'submitting'
                  ? 'Working…'
                  : briefingActionCtaLabel(action)
              }}
            </span>
          </button>
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

    <section class="galaxy-intelligence-panel__section">
      <button
        type="button"
        class="galaxy-intelligence-panel__host-toggle"
        :aria-expanded="hostContextOpen"
        @click="hostContextOpen = !hostContextOpen"
      >
        Host context
      </button>
      <HostCapabilityPanel v-if="hostContextOpen" />
    </section>
  </aside>
</template>
