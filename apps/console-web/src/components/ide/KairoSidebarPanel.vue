<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue';

import { useSpokenUtteranceText } from '../../composables/useSpokenUtteranceText';
import {
  briefingAdvise,
  briefingNotice,
  briefingPanelHeadline,
} from '../../lib/briefing-panel-view';
import { kairoPresenceLabel } from '../../lib/kairo-presence';
import { ideShowKairoSidebarExpanded, resolveIdeKairoChipState, shouldSurfaceIdeEmployeeFailure } from '../../lib/ide-presence-profile';
import { resolveIdePresencePersonaName } from '../../lib/ide-presence-persona';
import {
  clearKairoVoiceFollowupWindow,
  isKairoVoiceFollowupWindowActive,
  kairoVoiceFollowupExpiresAt,
} from '../../lib/kairo-voice-followup-window';
import {
  clearVaxonBriefingInteraction,
  recordVaxonBriefingInteraction,
  vaxonBriefingInteractionKey,
  vaxonBriefingPendingByWorkspace,
} from '../../lib/vaxon-briefing-interaction';
import { vaxonLineAsksForReply } from '../../lib/vaxon-reply-prompt';
import { employeeFailureDetailTooltip } from '../../features/workspace-agents/company-roster-view';
import { useShellStore } from '../../stores/shell';
import OperatorPersonaMark from '../OperatorPersonaMark.vue';
import AgentLiveLineHeadline from './AgentLiveLineHeadline.vue';
import KairoSidebarSpeechChip from './KairoSidebarSpeechChip.vue';
import { OPERATOR_PERSONA_NAME } from '../../lib/operator-persona-name';
import BriefingSurfaceFollowupPrompt from '../../features/kairo-conversation/BriefingSurfaceFollowupPrompt.vue';

const shell = useShellStore();
const { spokenText, speaker } = useSpokenUtteranceText();
const stickySpokenText = ref('');
const stickySpeakerName = ref('');
const stickyNeedsDecision = ref(false);
const followupTick = ref(0);
let followupTimer: ReturnType<typeof globalThis.setTimeout> | null = null;

watch(
  () => [spokenText.value, speaker.value?.name, speaker.value?.kind, speaker.value?.id] as const,
  ([text, name, kind, speakerId]) => {
    const next = text?.trim() ?? '';
    if (!next) {
      return;
    }
    stickySpokenText.value = next;
    const speakerName = name?.trim() || '';
    const activeEmployee = shell.activeIdeEmployee?.name?.trim() || '';
    stickySpeakerName.value =
      (speakerName && speakerName.toLowerCase() !== 'teammate'
        ? speakerName
        : null) ||
      (kind === 'vaxon' ? OPERATOR_PERSONA_NAME : activeEmployee) ||
      OPERATOR_PERSONA_NAME;
    const needsDecision = kind === 'vaxon' && vaxonLineAsksForReply(next);
    stickyNeedsDecision.value = needsDecision;
    // Only questions awaiting an operator answer persist; plain narration expires.
    if (needsDecision) {
      const ws = shell.currentWorkspace?.workspace_id?.trim();
      if (ws) {
        recordVaxonBriefingInteraction({
          workspaceId: ws,
          line: next,
          utteranceKey: vaxonBriefingInteractionKey(next, speakerId),
        });
      }
    }
  },
  { immediate: true },
);

watch(
  kairoVoiceFollowupExpiresAt,
  (expiresAt) => {
    if (followupTimer !== null) {
      globalThis.clearTimeout(followupTimer);
      followupTimer = null;
    }
    followupTick.value += 1;
    if (!expiresAt) {
      return;
    }
    const remaining = Math.max(0, expiresAt - Date.now());
    followupTimer = globalThis.setTimeout(() => {
      followupTick.value += 1;
      followupTimer = null;
    }, remaining + 50);
  },
  { immediate: true },
);

onMounted(() => {
  const ws = shell.currentWorkspace?.workspace_id?.trim();
  if (!ws) {
    return;
  }
  const pending = vaxonBriefingPendingByWorkspace.value[ws];
  if (!pending?.line.trim()) {
    return;
  }
  stickySpokenText.value = pending.line.trim();
  stickySpeakerName.value = OPERATOR_PERSONA_NAME;
  stickyNeedsDecision.value = vaxonLineAsksForReply(pending.line);
});

onBeforeUnmount(() => {
  if (followupTimer !== null) {
    globalThis.clearTimeout(followupTimer);
    followupTimer = null;
  }
});

const debugModeActive = computed(() => shell.ideDebugModeSelected);
const activePersonaName = computed(
  () => shell.activeIdeEmployee?.name?.trim() || OPERATOR_PERSONA_NAME,
);
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
const followupWindowActive = computed(() => {
  void followupTick.value;
  return isKairoVoiceFollowupWindowActive();
});
const pendingVaxonDecision = computed(() => {
  const ws = shell.currentWorkspace?.workspace_id?.trim();
  if (!ws) {
    return null;
  }
  return vaxonBriefingPendingByWorkspace.value[ws] ?? null;
});
const stickyDecisionActive = computed(
  () =>
    followupWindowActive.value ||
    stickyNeedsDecision.value ||
    Boolean(pendingVaxonDecision.value),
);
const presencePersonaName = computed(() =>
  resolveIdePresencePersonaName({
    speaker: speaker.value,
    kairoSpeechActive: shell.kairoSpeechActive,
    surfaceEmployeeFailure: surfaceEmployeeFailure.value,
    activeEmployeeName: shell.activeIdeEmployee?.name,
    stickySpeakerName: stickySpeakerName.value,
    stickyFollowupActive: stickyDecisionActive.value,
  }),
);
const activePersonaMark = computed(() =>
  presencePersonaName.value === OPERATOR_PERSONA_NAME
    ? null
    : shell.activeIdeEmployee?.initials ?? null,
);
const employeeFailureTooltip = computed(() => {
  const row = shell.activeIdeEmployeeRecord;
  if (!row) {
    return undefined;
  }
  return employeeFailureDetailTooltip(row) ?? shell.activeIdeEmployeeFailureLine ?? undefined;
});
const presenceLabel = computed(() => {
  // Live / sticky speech wins over stale failure chrome.
  if (
    shell.kairoSpeechActive ||
    speaker.value?.kind === 'employee' ||
    (stickyDecisionActive.value && stickySpeakerName.value.trim())
  ) {
    const state = shell.kairoSpeechActive ? 'speaking' : 'listening';
    return kairoPresenceLabel(state, presencePersonaName.value);
  }
  if (!debugModeActive.value && surfaceEmployeeFailure.value) {
    const hint = shell.activeIdeEmployeeShiftInterrupted
      ? 'shift interrupted'
      : 'last shift failed';
    return `${activePersonaName.value} · ${hint}`;
  }
  if (!debugModeActive.value) {
    return kairoPresenceLabel(shell.kairoPresenceState, presencePersonaName.value);
  }
  const access = shell.agentExecutionAccess === 'full' ? ' FULL' : '';
  const activity = shell.agentStreamActive ? ' · RUNNING' : '';
  return `${presencePersonaName.value} · DEBUG${access}${activity}`;
});

/** Team roster already fills the upper rail — keep presence as a chip there. */
const teamViewOpen = computed(
  () => shell.layoutMode === 'ide' && shell.ideActivityView === 'team',
);
const showExpandedPanel = computed(() => {
  if (teamViewOpen.value) {
    return false;
  }
  return ideShowKairoSidebarExpanded(shell.idePresenceProfile);
});

const showSpeechChip = computed(() => {
  if (shell.kairoSpeechActive || spokenText.value?.trim()) {
    return true;
  }
  // Decision prompts stay until the operator dismisses or replies.
  if (stickyNeedsDecision.value && stickySpokenText.value.trim()) {
    return true;
  }
  if (pendingVaxonDecision.value?.line.trim()) {
    return true;
  }
  if (stickySpokenText.value.trim() && followupWindowActive.value) {
    return true;
  }
  return showExpandedPanel.value;
});

const showSpeechDismiss = computed(
  () =>
    !shell.kairoSpeechActive &&
    Boolean(
      stickySpokenText.value.trim() ||
        pendingVaxonDecision.value?.line.trim(),
    ) &&
    (followupWindowActive.value ||
      stickyNeedsDecision.value ||
      Boolean(pendingVaxonDecision.value)),
);

function dismissSpeechChip(): void {
  clearKairoVoiceFollowupWindow();
  const ws = shell.currentWorkspace?.workspace_id?.trim();
  if (ws) {
    clearVaxonBriefingInteraction(ws);
  }
  stickySpokenText.value = '';
  stickySpeakerName.value = '';
  stickyNeedsDecision.value = false;
  followupTick.value += 1;
}

function onSpeechChipReplied(): void {
  dismissSpeechChip();
}

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
const speechPersonaName = computed(() => {
  if (speaker.value?.kind === 'vaxon' || stickySpeakerName.value === OPERATOR_PERSONA_NAME) {
    return OPERATOR_PERSONA_NAME;
  }
  return (
    stickySpeakerName.value.trim() ||
    speaker.value?.name?.trim() ||
    presencePersonaName.value ||
    OPERATOR_PERSONA_NAME
  );
});
const speechChipText = computed(
  () =>
    spokenText.value?.trim() ||
    stickySpokenText.value.trim() ||
    pendingVaxonDecision.value?.line.trim() ||
    null,
);
const showSpeechReplyBlock = computed(() => {
  const line = speechChipText.value?.trim() ?? '';
  if (!line) {
    return false;
  }
  const isVaxonSurface =
    speaker.value?.kind === 'vaxon' ||
    stickySpeakerName.value === OPERATOR_PERSONA_NAME ||
    Boolean(pendingVaxonDecision.value);
  if (!isVaxonSurface) {
    return false;
  }
  // VAXON questions / invites always get a reply surface in IDE.
  if (vaxonLineAsksForReply(line)) {
    return true;
  }
  // Duplex follow-up window after VAXON finishes speaking.
  return stickyDecisionActive.value;
});
const agentLinkLabel = computed(() => {
  if (shell.kairoSpeechActive) {
    return 'Voice live';
  }
  if (shell.agentStreamActive) {
    return 'Live stream';
  }
  if (surfaceEmployeeFailure.value || chipState.value === 'alerting') {
    return 'Attention';
  }
  return 'Standby';
});

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
  <div
    class="kairo-sidebar-panel-host"
    :class="{ 'kairo-sidebar-panel-host--team': teamViewOpen }"
  >
    <div
      v-if="!showExpandedPanel"
      class="kairo-sidebar-panel-compact-row"
    >
      <button
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
            'kairo-sidebar-panel--speaking': shell.kairoSpeechActive,
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
      <button
        v-if="showStopSpeech"
        type="button"
        class="kairo-sidebar-panel__compact-stop"
        @click="handleStopSpeech"
      >
        Stop
      </button>
    </div>
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
      :aria-label="`${presencePersonaName}. ${shell.briefingSummaryLine}`"
    >
      <div
        class="kairo-sidebar-panel__card"
        role="button"
        tabindex="0"
        :aria-label="`${presencePersonaName}. ${shell.briefingSummaryLine}`"
        @click="handleExpand"
        @keydown.enter.prevent="handleExpand"
        @keydown.space.prevent="handleExpand"
      >
        <p class="kairo-sidebar-panel__title">
          <OperatorPersonaMark size="sm" :mark="activePersonaMark" />
          <span class="kairo-sidebar-panel__eyebrow">Agent link</span>
          <span
            class="kairo-sidebar-panel__link-state"
            :data-state="chipState"
          >
            {{ agentLinkLabel }}
          </span>
        </p>
        <div class="kairo-sidebar-panel__body">
          <div class="kairo-sidebar-panel__radar" aria-hidden="true">
            <span class="kairo-sidebar-panel__ring kairo-sidebar-panel__ring--outer" />
            <span class="kairo-sidebar-panel__ring kairo-sidebar-panel__ring--mid" />
            <span class="kairo-sidebar-panel__ring kairo-sidebar-panel__ring--inner" />
            <span class="kairo-sidebar-panel__sweep" />
          </div>
          <div class="kairo-sidebar-panel__copy">
            <p class="kairo-sidebar-panel__state" aria-live="polite">
              <span
                class="kairo-sidebar-panel__state-dot"
                :data-state="chipState"
                aria-hidden="true"
              />
              <span>{{ presenceLabel }}</span>
            </p>
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
    </div>

    <KairoSidebarSpeechChip
      v-if="showSpeechChip"
      :spoken-text="speechChipText"
      :speaker="speaker"
      :speaking="shell.kairoSpeechActive"
      :fallback-persona-name="speechPersonaName"
      :sticky-text="stickySpokenText"
      :sticky-speaker-name="stickySpeakerName"
      :show-dismiss="showSpeechDismiss"
      :awaiting-reply="showSpeechReplyBlock"
      @stop-speech="handleStopSpeech()"
      @dismiss="dismissSpeechChip()"
      @replied="onSpeechChipReplied()"
    />
  </div>
</template>
