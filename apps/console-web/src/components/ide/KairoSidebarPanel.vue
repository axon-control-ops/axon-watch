<script setup lang="ts">
import { computed } from 'vue';

import { useSpokenUtteranceText } from '../../composables/useSpokenUtteranceText';
import {
  briefingAdvise,
  briefingNotice,
  briefingPanelHeadline,
} from '../../lib/briefing-panel-view';
import { kairoPresenceLabel } from '../../lib/kairo-presence';
import { ideShowKairoSidebarExpanded, resolveIdeKairoChipState, shouldSurfaceIdeEmployeeFailure } from '../../lib/ide-presence-profile';
import { employeeFailureDetailTooltip } from '../../features/workspace-agents/company-roster-view';
import { useShellStore } from '../../stores/shell';
import OperatorPersonaMark from '../OperatorPersonaMark.vue';
import AgentLiveLineHeadline from './AgentLiveLineHeadline.vue';
import KairoSidebarSpeechChip from './KairoSidebarSpeechChip.vue';
import { OPERATOR_PERSONA_NAME } from '../../lib/operator-persona-name';
import BriefingSurfaceFollowupPrompt from '../../features/kairo-conversation/BriefingSurfaceFollowupPrompt.vue';

const shell = useShellStore();
const { spokenText, speaker } = useSpokenUtteranceText();
const debugModeActive = computed(() => shell.ideDebugModeSelected);
const activePersonaName = computed(
  () => shell.activeIdeEmployee?.name?.trim() || OPERATOR_PERSONA_NAME,
);
const activePersonaMark = computed(() => shell.activeIdeEmployee?.initials ?? null);
const chipState = computed(() =>
  resolveIdeKairoChipState({
    profileState: shell.ideDisplayKairoPresenceState,
    employeeFailureLine: shell.activeIdeEmployeeFailureLine,
    agentStreamActive: shell.agentStreamActive,
    kairoSpeechActive: shell.kairoSpeechActive,
  }),
);
const surfaceEmployeeFailure = computed(() =>
  shouldSurfaceIdeEmployeeFailure({
    profileState: shell.ideDisplayKairoPresenceState,
    employeeFailureLine: shell.activeIdeEmployeeFailureLine,
    agentStreamActive: shell.agentStreamActive,
    kairoSpeechActive: shell.kairoSpeechActive,
  }),
);
const employeeFailureTooltip = computed(() => {
  const row = shell.activeIdeEmployeeRecord;
  if (!row) {
    return undefined;
  }
  return employeeFailureDetailTooltip(row) ?? shell.activeIdeEmployeeFailureLine ?? undefined;
});
const presenceLabel = computed(() => {
  if (!debugModeActive.value && surfaceEmployeeFailure.value) {
    const hint = shell.activeIdeEmployeeShiftInterrupted
      ? 'shift interrupted'
      : 'last shift failed';
    return `${activePersonaName.value} · ${hint}`;
  }
  if (!debugModeActive.value) {
    return kairoPresenceLabel(shell.kairoPresenceState, activePersonaName.value);
  }
  const access = shell.agentExecutionAccess === 'full' ? ' FULL' : '';
  const activity = shell.agentStreamActive ? ' · RUNNING' : '';
  return `${activePersonaName.value} · DEBUG${access}${activity}`;
});

const showExpandedPanel = computed(() =>
  ideShowKairoSidebarExpanded(shell.idePresenceProfile),
);

const briefingHeadline = computed(() =>
  briefingPanelHeadline(shell.operatorBriefing, shell.briefingLoadState),
);
const notice = computed(() => {
  if (shell.kairoSpeechActive || spokenText.value?.trim()) {
    return 'Spoken replies from the agent who is talking appear below.';
  }
  return briefingNotice(shell.operatorBriefing, shell.briefingLoadState);
});
const advise = computed(() =>
  briefingAdvise(shell.operatorBriefing, shell.briefingLoadState),
);
const approvalBadge = computed(() => shell.pendingApprovalsCount);
const signalBadge = computed(
  () => shell.operatorBriefing?.top_signals.length ?? shell.runtimeSummary?.signals.open_count ?? 0,
);
const showStopSpeech = computed(() => shell.kairoSpeechActive);
const speechPersonaName = computed(
  () => speaker.value?.name?.trim() || activePersonaName.value,
);

function handleExpand(): void {
  if (showStopSpeech.value) {
    shell.stopKairoSpeech();
    return;
  }
  if (surfaceEmployeeFailure.value) {
    shell.revealTeamRosterForActiveEmployee();
    return;
  }
  shell.focusKairoBriefing();
}

function handleStopSpeech(event?: Event): void {
  event?.stopPropagation();
  shell.stopKairoSpeech();
}
</script>

<template>
  <button
    v-if="!showExpandedPanel"
    id="ide-kairo-sidebar-panel"
    type="button"
    class="kairo-sidebar-panel kairo-sidebar-panel--compact"
    :class="[
      `kairo-sidebar-panel--${chipState}`,
      {
        'kairo-sidebar-panel--emphasized': shell.briefingSeamEmphasized,
        'kairo-sidebar-panel--debug-mode': debugModeActive,
        'kairo-sidebar-panel--employee-failed':
          surfaceEmployeeFailure && !shell.activeIdeEmployeeShiftInterrupted,
        'kairo-sidebar-panel--employee-interrupted':
          surfaceEmployeeFailure && shell.activeIdeEmployeeShiftInterrupted,
      },
    ]"
    :aria-label="presenceLabel"
    @click="handleExpand"
  >
    <span class="kairo-sidebar-panel__compact-dot" aria-hidden="true" />
    <span class="kairo-sidebar-panel__compact-label">
      {{ presenceLabel }}
    </span>
  </button>
  <div
    v-else
    id="ide-kairo-sidebar-panel"
    class="kairo-sidebar-panel kairo-sidebar-panel--expanded hud-panel-frame"
    :class="[
      `kairo-sidebar-panel--${shell.kairoPresenceState}`,
      {
        'kairo-sidebar-panel--emphasized': shell.briefingSeamEmphasized,
        'kairo-sidebar-panel--debug-mode': debugModeActive,
        'kairo-sidebar-panel--employee-failed':
          surfaceEmployeeFailure && !shell.activeIdeEmployeeShiftInterrupted,
        'kairo-sidebar-panel--employee-interrupted':
          surfaceEmployeeFailure && shell.activeIdeEmployeeShiftInterrupted,
        'kairo-sidebar-panel--alerting': chipState === 'alerting',
        'kairo-sidebar-panel--speaking': shell.kairoSpeechActive,
      },
    ]"
    :aria-label="`${activePersonaName}. ${shell.briefingSummaryLine}`"
  >
    <div
      class="kairo-sidebar-panel__card"
      role="button"
      tabindex="0"
      :aria-label="`${activePersonaName}. ${shell.briefingSummaryLine}`"
      @click="handleExpand"
      @keydown.enter.prevent="handleExpand"
      @keydown.space.prevent="handleExpand"
    >
      <p class="kairo-sidebar-panel__title">
        <OperatorPersonaMark size="sm" :mark="activePersonaMark" />
      </p>
      <div class="kairo-sidebar-panel__body">
        <div class="kairo-sidebar-panel__radar" aria-hidden="true">
          <span class="kairo-sidebar-panel__ring kairo-sidebar-panel__ring--outer" />
          <span class="kairo-sidebar-panel__ring kairo-sidebar-panel__ring--mid" />
          <span class="kairo-sidebar-panel__ring kairo-sidebar-panel__ring--inner" />
          <span class="kairo-sidebar-panel__sweep" />
        </div>
        <div class="kairo-sidebar-panel__copy">
          <p class="kairo-sidebar-panel__state">{{ presenceLabel }}</p>
          <p
            v-if="surfaceEmployeeFailure && !debugModeActive"
            class="kairo-sidebar-panel__employee-failure"
            :title="employeeFailureTooltip"
          >
            {{ shell.activeIdeEmployeeFailureLine }}
          </p>
          <AgentLiveLineHeadline
            class="kairo-sidebar-panel__headline"
            :activity="shell.ideComposerActivity"
            :fallback="briefingHeadline"
          />
          <p v-if="shell.briefingSummaryLine" class="kairo-sidebar-panel__summary">
            {{ shell.briefingSummaryLine }}
          </p>
          <p class="kairo-sidebar-panel__notice">{{ notice }}</p>
          <p v-if="advise" class="kairo-sidebar-panel__advise">{{ advise }}</p>
          <div v-if="approvalBadge || signalBadge" class="kairo-sidebar-panel__badges">
            <span v-if="approvalBadge" class="kairo-sidebar-panel__badge">
              {{ approvalBadge }} approval{{ approvalBadge === 1 ? '' : 's' }}
            </span>
            <span v-if="signalBadge" class="kairo-sidebar-panel__badge kairo-sidebar-panel__badge--signal">
              {{ signalBadge }} signal{{ signalBadge === 1 ? '' : 's' }}
            </span>
          </div>
          <button
            v-if="showStopSpeech"
            type="button"
            class="kairo-sidebar-panel__stop-speech"
            @click="handleStopSpeech"
          >
            Stop speaking
          </button>
        </div>
      </div>
      <BriefingSurfaceFollowupPrompt />
    </div>

    <KairoSidebarSpeechChip
      :spoken-text="spokenText"
      :speaker="speaker"
      :speaking="shell.kairoSpeechActive"
      :fallback-persona-name="speechPersonaName"
      @stop-speech="handleStopSpeech()"
    />
  </div>
</template>
