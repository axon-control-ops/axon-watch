<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue';

import { teammateRouteNotice } from '../../lib/teammate-route-notice';
import { runPhaseTag } from '../../lib/mockup-shell-view';
import { useShellStore } from '../../stores/shell';
import { formatSpecialtyRouteChip } from './specialty-dispatch-filament';
import {
  buildGalaxyAmbientPanels,
  galaxyAmbientSpokenLine,
  selectVisibleAmbientPanels,
} from './galaxy-ambient-hud-view';
import { kairoConversationPhase } from '../kairo-conversation/kairo-conversation-state';

const shell = useShellStore();
const nowMs = ref(Date.now());
let timer: number | null = null;

const presencePhase = computed(() => {
  if (shell.agentStreamActive) return 'autonomous';
  if (shell.kairoSpeechActive) return 'speaking';
  if (kairoConversationPhase.value === 'listening') return 'listening';
  if (kairoConversationPhase.value === 'thinking') return 'thinking';
  const critical =
    shell.operatorBriefing?.top_signals.filter((s) => s.severity === 'critical').length ?? 0;
  if (critical > 0) return 'alerting';
  return 'idle';
});

const hudInput = computed(() => {
  const briefing = shell.operatorBriefing;
  const critical =
    briefing?.top_signals.filter((signal) => signal.severity === 'critical').length ?? 0;
  const high = briefing?.top_signals.filter((signal) => signal.severity === 'high').length ?? 0;
  const top =
    briefing?.top_signals.find((signal) => signal.severity === 'critical') ??
    briefing?.top_signals[0] ??
    null;
  const notice = teammateRouteNotice.value;
  return {
    nowMs: nowMs.value,
    presencePhase: presencePhase.value,
    workspaceLabel:
      shell.currentWorkspace?.display_name ?? shell.currentWorkspace?.workspace_id ?? null,
    criticalSignals: critical,
    highSignals: high,
    runPhaseLabel: shell.primaryActiveRun ? runPhaseTag(shell.primaryActiveRun.phase) : null,
    topSignalTitle: top?.title ?? null,
    specialtyRouteLine: notice ? formatSpecialtyRouteChip(notice) : null,
    watchConnected: Boolean(briefing?.connectivity?.watch_connected ?? true),
  };
});

const panels = computed(() =>
  selectVisibleAmbientPanels(buildGalaxyAmbientPanels(hudInput.value), nowMs.value, 3200, 2),
);
const spoken = computed(() => galaxyAmbientSpokenLine(hudInput.value));

onMounted(() => {
  timer = window.setInterval(() => {
    nowMs.value = Date.now();
  }, 600);
});
onBeforeUnmount(() => {
  if (timer !== null) window.clearInterval(timer);
});
</script>

<template>
  <div class="kairo-orb-aura" aria-hidden="false">
    <p class="kairo-orb-aura__voice" aria-live="polite">{{ spoken }}</p>
    <TransitionGroup name="kairo-orb-sat" tag="div" class="kairo-orb-aura__sats">
      <article
        v-for="(panel, index) in panels"
        :key="panel.id"
        class="kairo-orb-aura__sat"
        :data-slot="index"
        :data-tone="panel.tone"
      >
        <header>{{ panel.title }}</header>
        <p>{{ panel.body }}</p>
      </article>
    </TransitionGroup>
  </div>
</template>
