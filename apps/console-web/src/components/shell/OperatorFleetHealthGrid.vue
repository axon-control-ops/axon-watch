<script setup lang="ts">
import { computed, ref } from 'vue';

import { useOrbFieldReactiveHost } from '../../composables/useOrbFieldReactiveHost';
import HudHoloPanelShell from '../../features/hud-holo/HudHoloPanelShell.vue';
import {
  fleetHealthToHoloTone,
  worstHudHoloTone,
  type HudHoloSignal,
  type HudHoloTone,
} from '../../features/hud-holo/hud-holo-tones';
import { companyBusyEmployees } from '../../features/workspace-agents/company-roster-busy';
import {
  buildFleetHealthGridCells,
  fleetHealthHeadlineWithCompanyBusy,
} from '../../lib/operator-fleet-health-view';
import { useShellStore } from '../../stores/shell';
import WorkspaceAddForm from './WorkspaceAddForm.vue';

const shell = useShellStore();
const rootEl = ref<HTMLElement | null>(null);
const showAddWorkspaceForm = ref(false);

useOrbFieldReactiveHost({
  root: rootEl,
  enabled: () => shell.layoutMode === 'operator' && shell.operatorBrainGalaxyActive,
});

const busyEmployeeCountByWorkspace = computed(() => {
  const counts: Record<string, number> = {};
  for (const employee of companyBusyEmployees(shell.companyEmployeesFleet)) {
    const workspaceId = employee.workspace_id?.trim();
    if (!workspaceId) {
      continue;
    }
    counts[workspaceId] = (counts[workspaceId] ?? 0) + 1;
  }
  return counts;
});

const companyBusyTotal = computed(() =>
  Object.values(busyEmployeeCountByWorkspace.value).reduce((sum, count) => sum + count, 0),
);

const cells = computed(() =>
  buildFleetHealthGridCells({
    snapshot: shell.operatorFleetHealth,
    workspaces: shell.workspaces,
    selectedWorkspaceId: shell.currentWorkspace?.workspace_id ?? null,
    busyEmployeeCountByWorkspace: busyEmployeeCountByWorkspace.value,
  }),
);

const headline = computed(() =>
  fleetHealthHeadlineWithCompanyBusy(shell.operatorFleetHealth, companyBusyTotal.value),
);

const anyBusy = computed(
  () =>
    cells.value.some((cell) => cell.isBusy) ||
    companyBusyTotal.value > 0 ||
    shell.agentStreamActive,
);

const holoTone = computed<HudHoloTone>(() =>
  worstHudHoloTone(cells.value.map((cell) => fleetHealthToHoloTone(cell.health))),
);

const holoSignals = computed<HudHoloSignal[]>(() =>
  cells.value.map((cell) => ({
    id: cell.workspaceId,
    tone: fleetHealthToHoloTone(cell.health),
    selected: cell.isSelected,
    weight: cell.isSelected ? 1 : cell.isBusy ? 0.95 : cell.health === 'nominal' ? 0.55 : 0.9,
  })),
);

function selectWorkspace(workspaceId: string): void {
  shell.setCurrentWorkspace(workspaceId);
}
</script>

<template>
  <div
    ref="rootEl"
    class="operator-fleet-grid-host"
    :class="{
      'operator-fleet-grid-host--orb-live': shell.voiceOrbDragging,
      'operator-fleet-grid-host--busy': anyBusy,
    }"
  >
    <HudHoloPanelShell
      class="operator-fleet-grid"
      :class="{ 'operator-fleet-grid--busy': anyBusy }"
      label="fleet-health"
      variant="module"
      :tone="holoTone"
      :signals="holoSignals"
      aria-label="Fleet health"
    >
      <header class="operator-fleet-grid__header" data-orb-field>
        <div>
          <p class="operator-fleet-grid__eyebrow">Second brain</p>
          <h3 class="operator-fleet-grid__title">Fleet health</h3>
        </div>
        <div class="operator-fleet-grid__header-meta">
          <span class="operator-fleet-grid__headline">{{ headline }}</span>
          <WorkspaceAddForm
            v-if="showAddWorkspaceForm"
            @registered="showAddWorkspaceForm = false"
            @cancel="showAddWorkspaceForm = false"
          />
          <button
            v-else
            type="button"
            class="operator-fleet-grid__new"
            @click="showAddWorkspaceForm = true"
          >
            + New Workspace
          </button>
        </div>
      </header>

      <p v-if="shell.operatorFleetHealthError" class="operator-fleet-grid__error" role="alert">
        {{ shell.operatorFleetHealthError }}
      </p>

      <ul v-else class="operator-fleet-grid__list">
        <li
          v-for="cell in cells"
          :key="cell.workspaceId"
          class="operator-fleet-grid__item"
          data-orb-field
          :class="[
            `operator-fleet-grid__item--${cell.health}`,
            {
              'operator-fleet-grid__item--selected': cell.isSelected,
              'operator-fleet-grid__item--busy': cell.isBusy,
              'operator-fleet-grid__item--has-attention':
                cell.openSignals > 0 || cell.pendingApprovals > 0 || cell.criticalSignals > 0,
            },
          ]"
        >
          <button
            type="button"
            class="operator-fleet-grid__button"
            :title="`${cell.label} — ${cell.summary}${cell.detail ? ` · ${cell.detail}` : ''}`"
            @click="selectWorkspace(cell.workspaceId)"
          >
            <span class="operator-fleet-grid__label-row">
              <span class="operator-fleet-grid__name">{{ cell.label }}</span>
            </span>
            <span class="operator-fleet-grid__badges">
              <span v-if="cell.isBoundProject" class="operator-fleet-grid__badge">project</span>
              <span v-if="cell.isBusy" class="operator-fleet-grid__badge operator-fleet-grid__badge--live">
                live
              </span>
              <span
                v-if="cell.criticalSignals > 0"
                class="operator-fleet-grid__badge operator-fleet-grid__badge--critical"
              >
                {{ cell.criticalSignals }} critical
              </span>
              <span
                v-else-if="cell.openSignals > 0"
                class="operator-fleet-grid__badge operator-fleet-grid__badge--signal"
              >
                {{ cell.openSignals }} signal{{ cell.openSignals === 1 ? '' : 's' }}
              </span>
              <span
                v-if="cell.pendingApprovals > 0"
                class="operator-fleet-grid__badge operator-fleet-grid__badge--approval"
              >
                {{ cell.pendingApprovals }} approval{{ cell.pendingApprovals === 1 ? '' : 's' }}
              </span>
              <span
                v-if="cell.reviewReady > 0"
                class="operator-fleet-grid__badge operator-fleet-grid__badge--review"
              >
                {{ cell.reviewReady }} review
              </span>
            </span>
            <span class="operator-fleet-grid__summary">{{ cell.summary }}</span>
            <span class="operator-fleet-grid__detail">{{ cell.detail }}</span>
          </button>
        </li>
      </ul>
    </HudHoloPanelShell>
  </div>
</template>
