<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue';

import { teammateRouteNotice } from '../../lib/teammate-route-notice';
import { useShellStore } from '../../stores/shell';
import { formatSpecialtyRouteChip } from './specialty-dispatch-filament';
import {
  buildGalaxyAmbientPanels,
  galaxyAmbientSpokenLine,
  selectVisibleAmbientPanels,
} from './galaxy-ambient-hud-view';
import type { GalaxyPresencePhase } from './galaxy-presence-state';
import { runPhaseTag } from '../../lib/mockup-shell-view';

const props = defineProps<{
  presencePhase: GalaxyPresencePhase;
}>();

const shell = useShellStore();
const nowMs = ref(Date.now());
let timer: number | null = null;

const specialtyRouteLine = computed(() => {
  const notice = teammateRouteNotice.value;
  return notice ? formatSpecialtyRouteChip(notice) : null;
});

const hudInput = computed(() => {
  const briefing = shell.operatorBriefing;
  const critical =
    briefing?.top_signals.filter((signal) => signal.severity === 'critical').length ?? 0;
  const high =
    briefing?.top_signals.filter((signal) => signal.severity === 'high').length ?? 0;
  const top =
    briefing?.top_signals.find((signal) => signal.severity === 'critical') ??
    briefing?.top_signals[0] ??
    null;
  return {
    nowMs: nowMs.value,
    presencePhase: props.presencePhase,
    workspaceLabel:
      shell.currentWorkspace?.display_name ?? shell.currentWorkspace?.workspace_id ?? null,
    criticalSignals: critical,
    highSignals: high,
    runPhaseLabel: shell.primaryActiveRun ? runPhaseTag(shell.primaryActiveRun.phase) : null,
    topSignalTitle: top?.title ?? null,
    specialtyRouteLine: specialtyRouteLine.value,
    watchConnected: Boolean(briefing?.connectivity?.watch_connected ?? true),
  };
});

const panels = computed(() =>
  selectVisibleAmbientPanels(buildGalaxyAmbientPanels(hudInput.value), nowMs.value),
);

const spoken = computed(() => galaxyAmbientSpokenLine(hudInput.value));

onMounted(() => {
  timer = window.setInterval(() => {
    nowMs.value = Date.now();
  }, 700);
});

onBeforeUnmount(() => {
  if (timer !== null) {
    window.clearInterval(timer);
  }
});
</script>

<template>
  <div class="galaxy-ambient-hud" aria-label="VAXON ambient activity">
    <p class="galaxy-ambient-hud__voice" aria-live="polite">{{ spoken }}</p>
    <TransitionGroup name="galaxy-ambient-panel" tag="div" class="galaxy-ambient-hud__panels">
      <article
        v-for="panel in panels"
        :key="panel.id"
        class="galaxy-ambient-hud__panel"
        :data-kind="panel.kind"
        :data-tone="panel.tone"
      >
        <header>{{ panel.title }}</header>
        <p>{{ panel.body }}</p>
      </article>
    </TransitionGroup>
  </div>
</template>
