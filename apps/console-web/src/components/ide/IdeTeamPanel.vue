<script setup lang="ts">
import { computed } from 'vue';

import { buildIdeActivityBarTeamAttention } from '../../lib/ide-activity-bar-view';
import { ideActivityPanelCollapseAriaLabel } from '../../lib/ide-activity-panel-view';
import HudHoloPanelShell from '../../features/hud-holo/HudHoloPanelShell.vue';
import type { HudHoloTone } from '../../features/hud-holo/hud-holo-tones';
import CompanyRosterPanel from '../shell/CompanyRosterPanel.vue';
import { useShellStore } from '../../stores/shell';

const shell = useShellStore();

const teamAttention = computed(() =>
  buildIdeActivityBarTeamAttention(shell.companyEmployeesForCurrentWorkspace),
);

const teamHoloTone = computed<HudHoloTone>(() => {
  if (teamAttention.value.tone === 'failure') {
    return 'critical';
  }
  if (teamAttention.value.tone === 'interrupted' || teamAttention.value.tone === 'mixed') {
    return 'attention';
  }
  return 'nominal';
});
</script>

<template>
  <HudHoloPanelShell
    v-if="!shell.ideExplorerCollapsed && shell.ideActivityView === 'team'"
    class="ide-explorer-panel ide-team-panel"
    :class="{
      'ide-team-panel--attention': teamAttention.tone === 'failure',
      'ide-team-panel--attention-interrupted': teamAttention.tone === 'interrupted',
      'ide-team-panel--attention-mixed': teamAttention.tone === 'mixed',
    }"
    label="team"
    :tone="teamHoloTone"
  >
    <div class="panel-heading ide-explorer-panel__heading">
      <p class="panel-heading__title">TEAM</p>
      <button
        type="button"
        class="panel-heading__action ide-explorer-panel__collapse"
        :aria-label="ideActivityPanelCollapseAriaLabel('team')"
        :title="ideActivityPanelCollapseAriaLabel('team')"
        @click="shell.toggleIdeExplorer()"
      >
        ‹
      </button>
    </div>
    <div class="ide-team-panel__body">
      <CompanyRosterPanel />
    </div>
  </HudHoloPanelShell>
</template>
