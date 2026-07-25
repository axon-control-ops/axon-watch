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
import {
  buildFleetHealthGridCells,
  fleetHealthHeadline,
} from '../../lib/operator-fleet-health-view';
import { useShellStore } from '../../stores/shell';

const shell = useShellStore();
const rootEl = ref<HTMLElement | null>(null);

useOrbFieldReactiveHost({ root: rootEl });

const cells = computed(() =>
  buildFleetHealthGridCells({
    snapshot: shell.operatorFleetHealth,
    workspaces: shell.workspaces,
    selectedWorkspaceId: shell.currentWorkspace?.workspace_id ?? null,
  }),
);

const headline = computed(() => fleetHealthHeadline(shell.operatorFleetHealth));

const holoTone = computed<HudHoloTone>(() =>
  worstHudHoloTone(cells.value.map((cell) => fleetHealthToHoloTone(cell.health))),
);

const holoSignals = computed<HudHoloSignal[]>(() =>
  cells.value.map((cell) => ({
    id: cell.workspaceId,
    tone: fleetHealthToHoloTone(cell.health),
    selected: cell.isSelected,
    weight: cell.isSelected ? 1 : cell.health === 'nominal' ? 0.55 : 0.9,
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
    :class="{ 'operator-fleet-grid-host--orb-live': shell.voiceOrbDragging }"
  >
    <HudHoloPanelShell
      class="operator-fleet-grid"
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
        <span class="operator-fleet-grid__headline">{{ headline }}</span>
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
            { 'operator-fleet-grid__item--selected': cell.isSelected },
          ]"
        >
          <button
            type="button"
            class="operator-fleet-grid__button"
            @click="selectWorkspace(cell.workspaceId)"
          >
            <span class="operator-fleet-grid__label">
              {{ cell.label }}
              <span v-if="cell.isBoundProject" class="operator-fleet-grid__badge">project</span>
            </span>
            <span class="operator-fleet-grid__summary">{{ cell.summary }}</span>
            <span class="operator-fleet-grid__detail">{{ cell.detail }}</span>
          </button>
        </li>
      </ul>
    </HudHoloPanelShell>
  </div>
</template>
