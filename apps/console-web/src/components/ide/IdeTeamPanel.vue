<script setup lang="ts">
import CompanyRosterPanel from '../shell/CompanyRosterPanel.vue';
import { useShellStore } from '../../stores/shell';

const shell = useShellStore();
</script>

<template>
  <section
    v-if="!shell.ideExplorerCollapsed && shell.ideActivityView === 'team'"
    class="ide-explorer-panel ide-team-panel hud-panel-frame"
  >
    <div class="panel-heading ide-explorer-panel__heading">
      <p class="panel-heading__title">TEAM</p>
      <button
        type="button"
        class="panel-heading__action ide-explorer-panel__collapse"
        aria-label="Collapse panel"
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
