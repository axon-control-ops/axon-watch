<script setup lang="ts">
import { computed } from 'vue';

import {
  operatorExecutionStage,
  operatorLiveFeed,
  operatorRadarTone,
  operatorStatusRail,
} from '../../lib/operator-status-radar-view';
import { leftSidebarAttentionBadgeCount } from '../../lib/left-sidebar-mode';
import { kairoPresenceModuleParts } from '../../lib/mockup-shell-view';
import { resolveKairoPresenceState } from '../../lib/kairo-presence';
import { useShellStore } from '../../stores/shell';

const props = defineProps<{
  terminalVisible: boolean;
}>();

const emit = defineEmits<{
  toggleTerminal: [];
}>();

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

const executionStage = computed(() =>
  operatorExecutionStage({
    workspaceId: workspaceId.value,
    runtimeSummary: shell.runtimeSummary,
    briefing: shell.operatorBriefing,
    loadState: shell.briefingLoadState,
    primaryActiveRun: shell.primaryActiveRun,
  }),
);

const liveFeed = computed(() =>
  operatorLiveFeed({
    historyRows: shell.runHistoryRows,
    currentStep: shell.primaryActiveRun?.current_step ?? null,
    lastAgentMessage:
      [...shell.threadMessages].reverse().find((message) => message.role === 'agent')?.content ??
      null,
    advise: executionStage.value.advise,
    hasActiveRun: executionStage.value.hasActiveRun,
  }),
);

const statusRail = computed(() =>
  operatorStatusRail({
    workspaceId: workspaceId.value,
    runtimeSummary: shell.runtimeSummary,
    briefing: shell.operatorBriefing,
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

const showStopAction = computed(
  () =>
    Boolean(shell.primaryActiveRun?.can_stop) ||
    shell.primaryActiveRun?.phase === 'executing',
);

const showLiveFeed = computed(
  () =>
    executionStage.value.hasActiveRun ||
    pendingApprovals.value > 0 ||
    shell.runHistoryRows.length > 0,
);

const showRunActions = computed(
  () =>
    showStopAction.value ||
    Boolean(shell.primaryActiveRun?.can_resume) ||
    shell.canCompletePrimaryRun ||
    shell.pendingApprovalsCount > 0,
);

const workspaceTerminalLabel = computed(() => {
  if (!workspaceId.value) {
    return 'No workspace selected';
  }

  return shell.runtimeSummary?.watch.connected
    ? `Connected · ${workspaceId.value}`
    : `Workspace · ${workspaceId.value}`;
});

function toggleTerminal(): void {
  emit('toggleTerminal');
}
</script>

<template>
  <section
    class="center-workbench__operator-status operator-status-radar-panel hud-panel-frame"
    :class="[
      `operator-status-radar-panel--${radarTone}`,
      {
        'operator-status-radar-panel--idle': !executionStage.hasActiveRun,
        'operator-status-radar-panel--terminal-collapsed': !props.terminalVisible,
      },
    ]"
    aria-label="Operator mission control"
  >
    <span class="hud-panel-frame__corner hud-panel-frame__corner--tl" aria-hidden="true" />
    <span class="hud-panel-frame__corner hud-panel-frame__corner--tr" aria-hidden="true" />
    <span class="hud-panel-frame__corner hud-panel-frame__corner--bl" aria-hidden="true" />
    <span class="hud-panel-frame__corner hud-panel-frame__corner--br" aria-hidden="true" />

    <header class="operator-status-radar-panel__header">
      <div class="operator-status-radar-panel__header-copy">
        <p class="operator-status-radar-panel__eyebrow">Operator center</p>
        <h2 class="operator-status-radar-panel__title">Mission Control</h2>
      </div>
      <div class="operator-status-radar-panel__header-actions">
        <button
          type="button"
          class="operator-status-radar-panel__terminal-chip"
          :class="{ 'operator-status-radar-panel__terminal-chip--collapsed': !props.terminalVisible }"
          @click="toggleTerminal"
        >
          {{ props.terminalVisible ? 'Terminal open' : 'Open terminal' }}
        </button>
        <div class="operator-status-radar-panel__presence">
          <span
            class="operator-status-radar-panel__status-dot"
            :class="`operator-status-radar-panel__status-dot--${radarTone}`"
            aria-hidden="true"
          />
          <div class="operator-status-radar-panel__presence-copy">
            <span class="operator-status-radar-panel__presence-title">{{ kairoParts.title }}</span>
            <span class="operator-status-radar-panel__presence-subtitle">{{ kairoParts.subtitle }}</span>
          </div>
        </div>
      </div>
    </header>

    <section class="operator-status-radar-panel__stage">
      <div class="operator-status-radar-panel__stage-top">
        <div class="operator-status-radar-panel__stage-identity">
          <span class="operator-status-radar-panel__phase-tag">{{ executionStage.phase }}</span>
          <span v-if="executionStage.hasActiveRun" class="operator-status-radar-panel__run-id">
            {{ executionStage.runId }}
          </span>
        </div>
        <span v-if="executionStage.hasActiveRun" class="operator-status-radar-panel__elapsed">
          {{ executionStage.elapsed }}
        </span>
      </div>

      <div
        v-if="executionStage.hasActiveRun"
        class="operator-status-radar-panel__progress"
        role="progressbar"
        :aria-valuenow="executionStage.phaseProgress"
        aria-valuemin="0"
        aria-valuemax="100"
        :aria-label="`${executionStage.phase} progress`"
      >
        <span
          class="operator-status-radar-panel__progress-fill"
          :style="{ width: `${executionStage.phaseProgress}%` }"
        />
      </div>

      <p class="operator-status-radar-panel__stage-step">{{ executionStage.currentStep }}</p>
      <p
        v-if="executionStage.hasActiveRun"
        class="operator-status-radar-panel__stage-summary"
      >
        {{ executionStage.summary }}
      </p>
      <p class="operator-status-radar-panel__stage-notice">{{ executionStage.notice }}</p>
      <p class="operator-status-radar-panel__stage-decide">{{ executionStage.decide }}</p>
      <p v-if="!executionStage.hasActiveRun" class="operator-status-radar-panel__stage-advise">
        {{ executionStage.advise }}
      </p>
    </section>

    <section
      v-if="showLiveFeed"
      class="operator-status-radar-panel__feed"
      aria-label="Live execution feed"
    >
      <header class="operator-status-radar-panel__section-header">
        <span>Live execution</span>
        <span>{{ shell.primaryActiveRun?.run_id ?? shell.threadStateLabel }}</span>
      </header>
      <ol class="operator-status-radar-panel__feed-list">
        <li
          v-for="item in liveFeed"
          :key="item.id"
          class="operator-status-radar-panel__feed-item"
          :class="`operator-status-radar-panel__feed-item--${item.tone}`"
        >
          <span class="operator-status-radar-panel__feed-marker" aria-hidden="true" />
          <div class="operator-status-radar-panel__feed-copy">
            <p>{{ item.label }}</p>
            <span v-if="item.meta">{{ item.meta }}</span>
          </div>
        </li>
      </ol>
    </section>

    <section v-if="showRunActions || shell.runMutationError" class="operator-status-radar-panel__controls">
      <div v-if="showRunActions" class="operator-status-radar-panel__run-actions run-actions">
        <button
          v-if="showStopAction"
          type="button"
          class="run-actions__button run-actions__button--primary"
          :disabled="!shell.canStopPrimaryRun && shell.primaryActiveRun?.phase !== 'executing'"
          @click="shell.stopPrimaryRun()"
        >
          {{ shell.runMutationState === 'stopping' ? 'STOPPING…' : 'STOP RUN' }}
        </button>
        <button
          v-if="shell.primaryActiveRun?.can_resume"
          type="button"
          class="run-actions__button run-actions__button--warning"
          :disabled="!shell.canResumePrimaryRun"
          @click="shell.resumePrimaryRun()"
        >
          {{ shell.runMutationState === 'resuming' ? 'RESUMING…' : 'RESUME RUN' }}
        </button>
        <button
          v-if="shell.canCompletePrimaryRun"
          type="button"
          class="run-actions__button run-actions__button--primary"
          :disabled="shell.runMutationPending"
          @click="shell.completePrimaryRun()"
        >
          {{ shell.runMutationState === 'completing' ? 'COMPLETING…' : 'COMPLETE RUN' }}
        </button>
        <template v-if="shell.pendingApprovalsCount > 0">
          <button
            type="button"
            class="run-actions__button run-actions__button--primary"
            :disabled="!shell.canApprovePrimaryRun"
            @click="shell.approvePrimaryRun()"
          >
            {{ shell.runMutationState === 'approving' ? 'APPROVING…' : 'APPROVE RUN' }}
          </button>
          <button
            type="button"
            class="run-actions__button run-actions__button--danger"
            :disabled="!shell.canRejectPrimaryRun"
            @click="shell.rejectPrimaryRun()"
          >
            {{ shell.runMutationState === 'rejecting' ? 'REJECTING…' : 'REJECT RUN' }}
          </button>
        </template>
      </div>

      <p v-if="shell.runMutationError" class="operator-status-radar-panel__error" role="alert">
        {{ shell.runMutationError }}
      </p>
    </section>

    <div class="operator-status-radar-panel__utility-actions">
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
    </div>

    <footer class="operator-status-radar-panel__rail" aria-label="Runtime status">
      <div
        v-for="item in statusRail"
        :key="item.label"
        class="operator-status-radar-panel__rail-item"
        :class="`operator-status-radar-panel__rail-item--${item.tone}`"
      >
        <span>{{ item.label }}</span>
        <strong>{{ item.value }}</strong>
      </div>
    </footer>

    <button
      v-if="!props.terminalVisible"
      type="button"
      class="operator-status-radar-panel__terminal-dock"
      @click="toggleTerminal"
    >
      <span class="operator-status-radar-panel__terminal-dock-label">Terminal dock</span>
      <span class="operator-status-radar-panel__terminal-dock-copy">{{ workspaceTerminalLabel }}</span>
      <span class="operator-status-radar-panel__terminal-dock-action">Show</span>
    </button>
  </section>
</template>
