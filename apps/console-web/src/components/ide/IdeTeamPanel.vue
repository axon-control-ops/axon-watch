<script setup lang="ts">
import { computed } from 'vue';

import { buildIdeActivityBarTeamAttention } from '../../lib/ide-activity-bar-view';
import { ideActivityPanelCollapseAriaLabel } from '../../lib/ide-activity-panel-view';
import CompanyRosterPanel from '../shell/CompanyRosterPanel.vue';
import { useShellStore } from '../../stores/shell';

const shell = useShellStore();

const teamAttention = computed(() =>
  buildIdeActivityBarTeamAttention(shell.companyEmployeesForCurrentWorkspace),
);
</script>

<template>
  <section
    v-if="!shell.ideExplorerCollapsed && shell.ideActivityView === 'team'"
    class="ide-explorer-panel ide-team-panel hud-panel-frame"
    :class="{
      'ide-team-panel--attention': teamAttention.tone === 'failure',
      'ide-team-panel--attention-interrupted': teamAttention.tone === 'interrupted',
      'ide-team-panel--attention-mixed': teamAttention.tone === 'mixed',
    }"
    aria-label="Team"
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
  </section>
</template>
