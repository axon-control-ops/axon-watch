<script setup lang="ts">
import HudSeamCard from '../HudSeamCard.vue';
import TerminalHost from '../TerminalHost.vue';
import { useShellStore } from '../../stores/shell';

const shell = useShellStore();
</script>

<template>
  <section class="region region-bottom-panel">
    <div v-if="shell.showDevSeams" class="region-header dev-scaffold">
      <div>
        <p class="eyebrow">Bottom Panel</p>
        <h2>Terminal and runtime strip host</h2>
      </div>
    </div>

    <div class="bottom-panel-grid">
      <HudSeamCard title="Terminal" class="bottom-panel-terminal">
        <TerminalHost
          :workspace-id="shell.currentWorkspace?.workspace_id ?? null"
          :run-summary="
            shell.primaryActiveRun
              ? `${shell.primaryActiveRun.run_id} · ${shell.primaryActiveRun.phase} · ${shell.primaryActiveRun.status}`
              : null
          "
          :primary-signal-id="shell.workspacePrimarySignal?.signal_id ?? null"
          :runtime-connected="Boolean(shell.runtimeSummary?.watch.connected)"
        />
      </HudSeamCard>

      <HudSeamCard v-if="shell.runtimeSummary" title="Runtime">
        <strong>
          {{ shell.runtimeSummary.runtime_identity.provider_name }} /
          {{ shell.runtimeSummary.runtime_identity.model_name }}
        </strong>
        <p class="region-copy">
          {{ shell.runtimeSummary.active_runs.length }} active run(s),
          {{ shell.runtimeSummary.signals.open_count }} open signal(s).
        </p>
      </HudSeamCard>

      <HudSeamCard v-else-if="shell.runtimeSummaryLoadState === 'error'" title="Runtime">
        <strong>Unavailable</strong>
        <p class="region-copy">{{ shell.runtimeSummaryError }}</p>
      </HudSeamCard>
    </div>
  </section>
</template>
