<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue';

import { openWatchConnectors } from '../../composables/useIdeEditorStatusBar';
import { buildOperatorQuickGuide, type OperatorQuickGuideActionId } from '../../lib/operator-quick-guide';
import {
  effectiveRequiredConnectorsUnavailable,
  isLegacyConnectorGlanceVisible,
} from '../../lib/connector-glance-view';
import {
  type OperatorCenterView,
} from '../../lib/operator-brain-graph-view';
import {
  operatorAgentSummary,
  operatorExecutionStage,
  operatorLiveFeed,
  operatorRadarTone,
  operatorStatusRail,
} from '../../lib/operator-status-radar-view';
import { shouldHideLiveExecutionFeed, isAutoCompleteRunSummary } from '../../lib/operator-run-strip-view';
import { leftSidebarAttentionBadgeCount } from '../../lib/left-sidebar-mode';
import { kairoPresenceModuleParts } from '../../lib/mockup-shell-view';
import PersonaTitle from '../PersonaTitle.vue';
import { resolveKairoPresenceState } from '../../lib/kairo-presence';
import {
  formatRunIdentityLabel,
} from '../../lib/run-display';
import { runContinueActionLabel } from '../../lib/run-lifecycle-ui';
import { useShellStore } from '../../stores/shell';
import {
  operatorTerminalDockActionLabel,
  workbenchTerminalPanelAlive,
  workbenchTerminalPanelAriaLabel,
  workbenchTerminalPanelTitle,
} from '../../lib/workbench-terminal-panel-view';
import ConnectorsRailPanel from './ConnectorsRailPanel.vue';
import OperatorBrainGraphPanel from './OperatorBrainGraphPanel.vue';
import OperatorFleetHealthGrid from './OperatorFleetHealthGrid.vue';
import OperatorIncidentFeedPanel from './OperatorIncidentFeedPanel.vue';
import OperatorRunStripPanel from './OperatorRunStripPanel.vue';
import OperatorStatusRadarPanelHeader from './OperatorStatusRadarPanelHeader.vue';
import OperatorStatusRadarQuickGuide from './operator-status-radar/OperatorStatusRadarQuickGuide.vue';
import OperatorTaskBoardPanel from './OperatorTaskBoardPanel.vue';
import AttentionStackPanel from './AttentionStackPanel.vue';

const props = defineProps<{
  terminalVisible: boolean;
}>();

const emit = defineEmits<{
  toggleTerminal: [];
}>();

const shell = useShellStore();

const continueActionLabel = computed(() =>
  runContinueActionLabel({
    phase: shell.primaryActiveRun?.phase,
    agentStreamActive: shell.agentStreamActive,
    mode: shell.primaryActiveRun?.mode,
    pending: shell.runMutationState === 'resuming',
    continueLabel: 'CONTINUE RUN',
    resumeLabel: 'RESUME RUN',
  }),
);

const centerView = computed(() => shell.operatorCenterView);
const brainHeroMode = computed(() => shell.operatorBrainGalaxyActive);

function setCenterView(view: OperatorCenterView): void {
  shell.setOperatorCenterView(view);
}

const workspaceId = computed(() => shell.currentWorkspace?.workspace_id ?? null);
const pendingApprovals = computed(
  () =>
    shell.operatorBriefing?.pending_approvals.count ??
    shell.runtimeSummary?.approvals.pending_count ??
    0,
);

const watchConnected = computed(() => shell.runtimeSummary?.watch.connected ?? false);

const requiredConnectorsUnavailable = computed(() =>
  effectiveRequiredConnectorsUnavailable(shell.connectorsSummary, watchConnected.value),
);

const radarTone = computed(() =>
  operatorRadarTone({
    runtimeSummary: shell.runtimeSummary,
    briefing: shell.operatorBriefing,
    pendingApprovals: pendingApprovals.value,
    requiredConnectorsUnavailable: requiredConnectorsUnavailable.value,
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
    requiredConnectorsUnavailable: requiredConnectorsUnavailable.value,
  }),
);

const liveFeed = computed(() =>
  operatorLiveFeed({
    historyRows: shell.runHistoryRows,
    currentStep: shell.primaryActiveRun?.current_step ?? null,
    lastAgentMessage: shell.latestWorkspaceAgentOutput,
    advise: executionStage.value.advise,
    hasActiveRun: executionStage.value.hasActiveRun,
  }),
);

const agentSummary = computed(() =>
  operatorAgentSummary({
    historyRows: shell.runHistoryRows,
    currentStep: shell.primaryActiveRun?.current_step ?? null,
    lastAgentMessage: shell.latestWorkspaceAgentOutput,
  }),
);

const statusRail = computed(() =>
  operatorStatusRail({
    workspaceId: workspaceId.value,
    runtimeSummary: shell.runtimeSummary,
    briefing: shell.operatorBriefing,
    pendingApprovals: pendingApprovals.value,
    connectorsLoadState: shell.connectorsLoadState,
    connectorsSummary: shell.connectorsSummary,
  }),
);

function handleStatusRailAction(action: 'focus-connectors'): void {
  if (action === 'focus-connectors') {
    openWatchConnectors(shell);
  }
}

const attentionBadgeCount = computed(() =>
  leftSidebarAttentionBadgeCount({
    pendingApprovals: pendingApprovals.value,
    briefing: shell.operatorBriefing,
    inboxItems: shell.inboxItems,
    inboxLoadState: shell.inboxLoadState,
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

const onlyAutoCompleteReviewBacklog = computed(
  () =>
    reviewReadyRuns.value.length > 0 &&
    reviewReadyRuns.value.every((run) => isAutoCompleteRunSummary(run.summary)) &&
    pendingApprovals.value === 0 &&
    (!shell.primaryActiveRun || shell.primaryActiveRun.phase === 'review_ready'),
);

const showLiveFeed = computed(
  () =>
    !shouldHideLiveExecutionFeed({
      reviewReadyRuns: reviewReadyRuns.value,
      primaryActiveRun: shell.primaryActiveRun,
    }) &&
    (executionStage.value.hasActiveRun ||
      pendingApprovals.value > 0 ||
      shell.runHistoryRows.length > 0),
);

const showMissionStage = computed(
  () =>
    !onlyAutoCompleteReviewBacklog.value &&
    (executionStage.value.hasActiveRun ||
      pendingApprovals.value > 0 ||
      shell.canResumePrimaryRun ||
      shell.canCompletePrimaryRun),
);

const showRunActions = computed(
  () =>
    !onlyAutoCompleteReviewBacklog.value &&
    (showStopAction.value ||
      shell.canResumePrimaryRun ||
      shell.canCompletePrimaryRun ||
      shell.pendingApprovalsCount > 0),
);

const legacyConnectorGlanceVisible = computed(() =>
  isLegacyConnectorGlanceVisible({
    connectorsLoadState: shell.connectorsLoadState,
    items: shell.connectorsItems,
    summary: shell.connectorsSummary,
    watchConnected: shell.runtimeSummary?.watch.connected ?? false,
    layoutMode: shell.layoutMode,
  }),
);

const quickGuide = computed(() =>
  buildOperatorQuickGuide({
    runPhase: shell.primaryActiveRun?.phase ?? null,
    hasActiveRun: executionStage.value.hasActiveRun,
    pendingApprovals: pendingApprovals.value,
    layoutMode: shell.layoutMode,
    terminalVisible: props.terminalVisible,
    legacyConnectorGlanceVisible: legacyConnectorGlanceVisible.value,
    requiredConnectorsUnavailable: requiredConnectorsUnavailable.value,
  }),
);

// Idle Grid stays readable: only attention guides overlay as standalone cards.
const showStandaloneQuickGuide = computed(
  () =>
    !showMissionStage.value &&
    Boolean(quickGuide.value) &&
    quickGuide.value?.tone === 'attention',
);

onMounted(() => {
  if (
    shell.operatorFleetHealthLoadState === 'idle' ||
    shell.operatorFleetHealthLoadState === 'error'
  ) {
    void shell.loadOperatorFleetHealth();
  }
  if (shell.currentWorkspace?.workspace_id) {
    void shell.loadWorkspaceTasks(shell.currentWorkspace.workspace_id);
  }
  // Park the Brain Graph floating orb after stage chrome exists in the DOM.
  // Skip when the operator pinned a custom placement (persisted across refresh).
  window.setTimeout(() => {
    if (
      shell.layoutMode === 'operator' &&
      shell.operatorBrainGalaxyActive &&
      shell.voiceOrbVisible &&
      !shell.voiceOrbUserPinned
    ) {
      shell.requestVoiceOrbSmartDodge({ preferredDock: 'bottom-left' });
    }
  }, 80);
});

const terminalRunPhase = computed(() => shell.primaryActiveRun?.phase ?? null);

const terminalDockAlive = computed(
  () => !props.terminalVisible && workbenchTerminalPanelAlive(terminalRunPhase.value),
);

const terminalPanelTitle = computed(() =>
  workbenchTerminalPanelTitle(props.terminalVisible, terminalRunPhase.value),
);

const terminalPanelAriaLabel = computed(() =>
  workbenchTerminalPanelAriaLabel(props.terminalVisible, terminalRunPhase.value),
);

const workspaceTerminalLabel = computed(() => {
  if (!workspaceId.value) {
    return 'No workspace selected';
  }

  const workspacePart = shell.runtimeSummary?.watch.connected
    ? `Connected · ${workspaceId.value}`
    : `Workspace · ${workspaceId.value}`;

  if (!props.terminalVisible && terminalRunPhase.value === 'executing') {
    return `Run in progress · ${workspacePart}`;
  }

  if (!props.terminalVisible && terminalRunPhase.value === 'review_ready') {
    return `Review ready · ${workspacePart}`;
  }

  return workspacePart;
});

function toggleTerminal(): void {
  emit('toggleTerminal');
}

function handleOperatorQuickGuideAction(actionId: OperatorQuickGuideActionId): void {
  if (actionId === 'show-terminal') {
    toggleTerminal();
    return;
  }

  if (actionId === 'open-attention') {
    shell.focusAttentionSidebar();
    return;
  }

  if (actionId === 'open-briefing') {
    shell.focusKairoBriefing();
    return;
  }

  if (actionId === 'open-connectors') {
    openWatchConnectors(shell);
    return;
  }

  if (actionId === 'switch-to-ide') {
    shell.setLayoutMode('ide');
  }
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
        'operator-status-radar-panel--galaxy-only': brainHeroMode,
      },
    ]"
    aria-label="Operator mission control"
  >
    <template v-if="brainHeroMode">
      <OperatorBrainGraphPanel
        :terminal-visible="props.terminalVisible"
        @toggle-terminal="toggleTerminal"
        @switch-grid="setCenterView('grid')"
      />
    </template>

    <template v-else>
      <span class="hud-panel-frame__corner hud-panel-frame__corner--tl" aria-hidden="true" />
      <span class="hud-panel-frame__corner hud-panel-frame__corner--tr" aria-hidden="true" />
      <span class="hud-panel-frame__corner hud-panel-frame__corner--bl" aria-hidden="true" />
      <span class="hud-panel-frame__corner hud-panel-frame__corner--br" aria-hidden="true" />

      <OperatorStatusRadarPanelHeader
        :center-view="centerView"
        :radar-tone="radarTone"
        :terminal-visible="props.terminalVisible"
        :terminal-dock-alive="terminalDockAlive"
        :terminal-run-phase="terminalRunPhase"
        :terminal-panel-title="terminalPanelTitle"
        :terminal-panel-aria-label="terminalPanelAriaLabel"
        :kairo-title="kairoParts.title"
        :kairo-subtitle="kairoParts.subtitle"
        :show-kairo-presence="centerView !== 'grid'"
        @set-center-view="setCenterView"
        @toggle-terminal="toggleTerminal"
      />

      <OperatorFleetHealthGrid />

      <section
        id="mission-control-attention"
        class="operator-status-radar-panel__attention"
        aria-label="Attention for current workspace"
      >
        <header class="operator-status-radar-panel__attention-head">
          <p class="operator-status-radar-panel__attention-eyebrow">Attention</p>
          <p class="operator-status-radar-panel__attention-scope">
            {{
              shell.currentWorkspace?.display_name?.trim() ||
              shell.currentWorkspace?.workspace_id ||
              'Current workspace'
            }}
          </p>
        </header>
        <AttentionStackPanel variant="sidebar" sections="attention-only" />
      </section>

      <OperatorTaskBoardPanel />

      <OperatorIncidentFeedPanel />

      <OperatorRunStripPanel />

      <OperatorStatusRadarQuickGuide
        v-if="showStandaloneQuickGuide && quickGuide"
        :guide="quickGuide"
        :terminal-visible="props.terminalVisible"
        standalone
        @action="handleOperatorQuickGuideAction"
      />

      <section
        v-if="showMissionStage"
        class="operator-status-radar-panel__stage"
      >
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

        <p class="operator-status-radar-panel__stage-notice">{{ executionStage.notice }}</p>
        <p class="operator-status-radar-panel__stage-decide">{{ executionStage.decide }}</p>

        <OperatorStatusRadarQuickGuide
          v-if="quickGuide"
          :guide="quickGuide"
          :terminal-visible="props.terminalVisible"
          @action="handleOperatorQuickGuideAction"
        />

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

      <section
        class="operator-status-radar-panel__feed"
        aria-label="Agent summary"
      >
        <header class="operator-status-radar-panel__section-header">
          <span>Agent summary</span>
          <span>{{ shell.primaryActiveRun ? formatRunIdentityLabel(shell.primaryActiveRun) : 'Latest run state' }}</span>
        </header>
        <ol class="operator-status-radar-panel__feed-list">
          <li
            v-for="item in agentSummary"
            :key="item.id"
            class="operator-status-radar-panel__feed-item operator-status-radar-panel__feed-item--info"
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
            v-if="shell.canResumePrimaryRun"
            type="button"
            class="run-actions__button run-actions__button--warning"
            :disabled="!shell.canResumePrimaryRun || shell.runMutationPending"
            @click="shell.resumePrimaryRun()"
          >
            {{ continueActionLabel }}
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
          Open <PersonaTitle suffix="Briefing" mark-size="xs" />
        </button>
      </div>

      <footer class="operator-status-radar-panel__rail" aria-label="Runtime status">
        <component
          :is="item.action ? 'button' : 'div'"
          v-for="item in statusRail"
          :key="item.label"
          class="operator-status-radar-panel__rail-item"
          :class="[
            `operator-status-radar-panel__rail-item--${item.tone}`,
            { 'operator-status-radar-panel__rail-item--action': item.action },
          ]"
          :type="item.action ? 'button' : undefined"
          :title="item.action === 'focus-connectors' ? 'Open Mission Control connectors' : undefined"
          :aria-label="
            item.action === 'focus-connectors'
              ? `${item.label} ${item.value}. Open Mission Control connectors.`
              : undefined
          "
          @click="item.action ? handleStatusRailAction(item.action) : undefined"
        >
          <span>{{ item.label }}</span>
          <strong>{{ item.value }}</strong>
        </component>
      </footer>

      <button
        v-if="!props.terminalVisible"
        type="button"
        class="operator-status-radar-panel__terminal-dock"
        :class="{
          'operator-status-radar-panel__terminal-dock--alive': terminalDockAlive,
          'operator-status-radar-panel__terminal-dock--executing':
            terminalRunPhase === 'executing',
          'operator-status-radar-panel__terminal-dock--review-ready':
            terminalRunPhase === 'review_ready',
        }"
        :title="terminalPanelTitle"
        :aria-label="terminalPanelAriaLabel"
        @click="toggleTerminal"
      >
        <span class="operator-status-radar-panel__terminal-dock-label">
          Terminal dock
          <span
            v-if="terminalDockAlive"
            class="operator-status-radar-panel__terminal-dock-pulse"
            aria-hidden="true"
          />
        </span>
        <span class="operator-status-radar-panel__terminal-dock-copy">{{ workspaceTerminalLabel }}</span>
        <span class="operator-status-radar-panel__terminal-dock-action">
          {{ operatorTerminalDockActionLabel(false) }}
        </span>
      </button>
    </template>
  </section>
</template>
