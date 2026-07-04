<script setup lang="ts">
import { computed } from 'vue';

import {
  operatorRadarTone,
  operatorStatusAdvise,
  operatorStatusHeadline,
  operatorStatusMetrics,
} from '../../lib/operator-status-radar-view';
import { leftSidebarAttentionBadgeCount } from '../../lib/left-sidebar-mode';
import { kairoPresenceModuleParts } from '../../lib/mockup-shell-view';
import { resolveKairoPresenceState } from '../../lib/kairo-presence';
import { useShellStore } from '../../stores/shell';

const shell = useShellStore();

const workspaceId = computed(() => shell.currentWorkspace?.workspace_id ?? null);
const pendingApprovals = computed(
  () =>
    shell.operatorBriefing?.pending_approvals.count ??
    shell.runtimeSummary?.approvals.pending_count ??
    0,
);

const radarTone = computed(() =>
  operatorRadarTone({
    runtimeSummary: shell.runtimeSummary,
    briefing: shell.operatorBriefing,
    pendingApprovals: pendingApprovals.value,
  }),
);

const headline = computed(() =>
  operatorStatusHeadline({
    briefing: shell.operatorBriefing,
    loadState: shell.briefingLoadState,
    primaryActiveRun: shell.primaryActiveRun,
  }),
);

const advise = computed(() =>
  operatorStatusAdvise({
    briefing: shell.operatorBriefing,
    loadState: shell.briefingLoadState,
  }),
);

const metrics = computed(() =>
  operatorStatusMetrics({
    workspaceId: workspaceId.value,
    runtimeSummary: shell.runtimeSummary,
    runtimeSummaryLoadState: shell.runtimeSummaryLoadState,
    briefing: shell.operatorBriefing,
    briefingLoadState: shell.briefingLoadState,
    primaryActiveRun: shell.primaryActiveRun,
    pendingApprovals: pendingApprovals.value,
  }),
);

const attentionBadgeCount = computed(() =>
  leftSidebarAttentionBadgeCount({
    pendingApprovals: pendingApprovals.value,
    briefing: shell.operatorBriefing,
  }),
);

const kairoParts = computed(() => {
  const highSignals =
    shell.operatorBriefing?.top_signals.filter((signal) => signal.severity === 'high').length ??
    0;
  const criticalSignals =
    shell.operatorBriefing?.top_signals.filter((signal) => signal.severity === 'critical')
      .length ?? 0;
  const state = resolveKairoPresenceState({
    pendingApprovals: pendingApprovals.value,
    criticalSignals,
    highSignals,
    watchConnected: shell.runtimeSummary?.watch.connected ?? false,
    runtimeLoaded: shell.runtimeSummaryLoadState === 'loaded',
  });
  return kairoPresenceModuleParts(state);
});
</script>

<template>
  <section
    class="center-workbench__operator-status operator-status-radar-panel hud-panel-frame"
    :class="`operator-status-radar-panel--${radarTone}`"
    aria-label="Operator status"
  >
    <span class="hud-panel-frame__corner hud-panel-frame__corner--tl" aria-hidden="true" />
    <span class="hud-panel-frame__corner hud-panel-frame__corner--tr" aria-hidden="true" />
    <span class="hud-panel-frame__corner hud-panel-frame__corner--bl" aria-hidden="true" />
    <span class="hud-panel-frame__corner hud-panel-frame__corner--br" aria-hidden="true" />

    <header class="operator-status-radar-panel__header">
      <div>
        <p class="operator-status-radar-panel__eyebrow">Operator center</p>
        <h2 class="operator-status-radar-panel__title">STATUS / RADAR</h2>
      </div>
      <div class="operator-status-radar-panel__presence">
        <span class="operator-status-radar-panel__presence-title">{{ kairoParts.title }}</span>
        <span class="operator-status-radar-panel__presence-subtitle">{{ kairoParts.subtitle }}</span>
      </div>
    </header>

    <div class="operator-status-radar-panel__body">
      <div class="operator-status-radar-panel__radar-wrap" aria-hidden="true">
        <div class="operator-status-radar-panel__radar">
          <span class="operator-status-radar-panel__ring operator-status-radar-panel__ring--outer" />
          <span class="operator-status-radar-panel__ring operator-status-radar-panel__ring--mid" />
          <span class="operator-status-radar-panel__ring operator-status-radar-panel__ring--inner" />
          <span class="operator-status-radar-panel__crosshair operator-status-radar-panel__crosshair--h" />
          <span class="operator-status-radar-panel__crosshair operator-status-radar-panel__crosshair--v" />
          <span class="operator-status-radar-panel__tick operator-status-radar-panel__tick--n" />
          <span class="operator-status-radar-panel__tick operator-status-radar-panel__tick--e" />
          <span class="operator-status-radar-panel__tick operator-status-radar-panel__tick--s" />
          <span class="operator-status-radar-panel__tick operator-status-radar-panel__tick--w" />
          <span class="operator-status-radar-panel__sweep" />
          <span class="operator-status-radar-panel__core" />
        </div>
      </div>

      <div class="operator-status-radar-panel__copy">
        <p class="operator-status-radar-panel__headline">{{ headline }}</p>
        <p class="operator-status-radar-panel__advise">{{ advise }}</p>

        <dl class="operator-status-radar-panel__metrics">
          <div
            v-for="metric in metrics"
            :key="metric.label"
            class="operator-status-radar-panel__metric"
            :class="`operator-status-radar-panel__metric--${metric.tone}`"
          >
            <dt>{{ metric.label }}</dt>
            <dd>{{ metric.value }}</dd>
          </div>
        </dl>
      </div>
    </div>

    <footer class="operator-status-radar-panel__actions">
      <button
        type="button"
        class="operator-status-radar-panel__action"
        @click="shell.setLeftSidebarMode('attention')"
      >
        Open Attention
        <span v-if="attentionBadgeCount > 0" class="operator-status-radar-panel__badge">
          {{ attentionBadgeCount }}
        </span>
      </button>
      <button
        type="button"
        class="operator-status-radar-panel__action operator-status-radar-panel__action--kairo"
        @click="shell.focusKairoBriefing()"
      >
        Open KAIRO Briefing
      </button>
    </footer>
  </section>
</template>
