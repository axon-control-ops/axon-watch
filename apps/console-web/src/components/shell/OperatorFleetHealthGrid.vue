<script setup lang="ts">
import { computed } from 'vue';

import {
  buildFleetHealthGridCells,
  fleetHealthHeadline,
} from '../../lib/operator-fleet-health-view';
import { useShellStore } from '../../stores/shell';

const shell = useShellStore();

const cells = computed(() =>
  buildFleetHealthGridCells({
    snapshot: shell.operatorFleetHealth,
    workspaces: shell.workspaces,
    selectedWorkspaceId: shell.currentWorkspace?.workspace_id ?? null,
  }),
);

const headline = computed(() => fleetHealthHeadline(shell.operatorFleetHealth));

function selectWorkspace(workspaceId: string): void {
  shell.setCurrentWorkspace(workspaceId);
}
</script>

<template>
  <section class="operator-fleet-grid" aria-label="Fleet health">
    <header class="operator-fleet-grid__header">
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
  </section>
</template>
