<script setup lang="ts">
import { computed } from 'vue';

import { buildOperatorQuickGuide } from '../../lib/operator-quick-guide';
import {
  operatorExecutionStage,
  operatorLiveFeed,
  operatorRadarTone,
  operatorStatusRail,
} from '../../lib/operator-status-radar-view';
import { leftSidebarAttentionBadgeCount } from '../../lib/left-sidebar-mode';
import { kairoPresenceModuleParts } from '../../lib/mockup-shell-view';
import { resolveKairoPresenceState } from '../../lib/kairo-presence';
import {
  formatRunDisplayName,
  formatRunIdentityLabel,
  formatRunShortId,
} from '../../lib/run-display';
import { useShellStore } from '../../stores/shell';
import ConnectorsRailPanel from './ConnectorsRailPanel.vue';

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

const reviewReadyRuns = computed(() =>
  shell.runs.filter(
    (run) =>
      run.phase === 'review_ready' &&
      run.workspace_id === shell.currentWorkspace?.workspace_id,
  ),
);

const executionStage = computed(() =>
  operatorExecutionStage({
    workspaceId: workspaceId.value,
    runtimeSummary: shell.runtimeSummary,
    briefing: shell.operatorBriefing,
    loadState: shell.briefingLoadState,
    primaryActiveRun: shell.primaryActiveRun,
    workspaceReviewReadyCount: reviewReadyRuns.value.length,
  }),
);

const liveFeed = computed(() =>
  operatorLiveFeed({
    historyRows: shell.runHistoryRows,
    currentStep: shell.primaryActiveRun?.current_step ?? null,
    lastAgentMessage:
      [...shell.operatorThreadMessages].reverse().find((message) => message.role === 'agent')
        ?.content ?? null,
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

const quickGuide = computed(() =>
  buildOperatorQuickGuide({
    runPhase: shell.primaryActiveRun?.phase ?? null,
    hasActiveRun: executionStage.value.hasActiveRun,
    pendingApprovals: pendingApprovals.value,
    layoutMode: shell.layoutMode,
  }),
);

const reviewReadyRunsShown = computed(() => reviewReadyRuns.value.slice(0, 5));
const reviewReadyRunsOverflow = computed(() =>
  Math.max(0, reviewReadyRuns.value.length - reviewReadyRunsShown.value.length),
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
    id="operator-mission-control"
    class="center-workbench__operator-status operator-status-radar-panel hud-panel-frame"
    :class="[
      `operator-status-radar-panel--${radarTone}`,
      {
        'operator-status-radar-panel--idle': !executionStage.hasActiveRun,
        'operator-status-radar-panel--terminal-collapsed': !props.terminalVisible,
        'operator-status-radar-panel--emphasized': shell.missionControlEmphasized,
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
            {{ executionStage.displayName }}
            <span class="operator-status-radar-panel__run-short-id">#{{ executionStage.shortId }}</span>
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
        Task: {{ executionStage.summary }}
        <span v-if="executionStage.commandDetail"> · Command: {{ executionStage.commandDetail }}</span>
      </p>

      <section
        v-if="reviewReadyRuns.length > 1"
        class="operator-status-radar-panel__run-queue"
        aria-label="Runs waiting for review"
      >
        <div class="operator-status-radar-panel__run-queue-header">
          <p class="operator-status-radar-panel__run-queue-title">
            {{ reviewReadyRuns.length }} tasks waiting — complete each when done
          </p>
          <button
            type="button"
            class="operator-status-radar-panel__run-queue-clear"
            :disabled="shell.runMutationPending"
            @click="shell.completeAllReviewReadyRuns()"
          >
            {{ shell.runMutationState === 'completing' ? 'Completing…' : 'Complete all' }}
          </button>
        </div>
        <ul class="operator-status-radar-panel__run-queue-list">
          <li
            v-for="run in reviewReadyRunsShown"
            :key="run.run_id"
            class="operator-status-radar-panel__run-queue-item"
            :class="{
              'operator-status-radar-panel__run-queue-item--primary':
                run.run_id === shell.primaryActiveRun?.run_id,
            }"
          >
            <span>{{ formatRunDisplayName(run) }}</span>
            <span>#{{ formatRunShortId(run.run_id) }}</span>
          </li>
        </ul>
        <p v-if="reviewReadyRunsOverflow > 0" class="operator-status-radar-panel__run-queue-more">
          + {{ reviewReadyRunsOverflow }} more in run history — complete the primary run first
        </p>
      </section>
      <p class="operator-status-radar-panel__stage-notice">{{ executionStage.notice }}</p>
      <p class="operator-status-radar-panel__stage-decide">{{ executionStage.decide }}</p>

      <section
        v-if="quickGuide"
        class="operator-status-radar-panel__guide"
        aria-label="What to do next"
      >
        <p class="operator-status-radar-panel__guide-title">{{ quickGuide.title }}</p>
        <ol class="operator-status-radar-panel__guide-steps">
          <li v-for="(step, index) in quickGuide.steps" :key="index">{{ step }}</li>
        </ol>
      </section>

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
        <span>{{ shell.primaryActiveRun ? formatRunIdentityLabel(shell.primaryActiveRun) : shell.threadStateLabel }}</span>
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
          v-if="shell.primaryActiveRun?.can_resume && shell.primaryActiveRun?.phase !== 'review_ready'"
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

    <ConnectorsRailPanel />

    <div class="operator-status-radar-panel__utility-actions">
      <button
        type="button"
        class="operator-status-radar-panel__action"
        @click="shell.focusAttentionSidebar()"
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
