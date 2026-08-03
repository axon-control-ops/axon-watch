<script setup lang="ts">
import { computed, onMounted, onUnmounted, watch } from 'vue';

import AgentDockTeammateRouteBanner from '../../components/ide/agent-dock/AgentDockTeammateRouteBanner.vue';
import {
  kairoConversationError,
  kairoConversationPhase,
  kairoConversationReply,
  setKairoConversationPhase,
} from './kairo-conversation-state';
import { useKairoConversation } from './use-kairo-conversation';
import { registerKairoConversationSubmit } from './kairo-conversation-bus';
import OperatorPersonaMark from '../../components/OperatorPersonaMark.vue';
import { OPERATOR_PERSONA_NAME } from '../../lib/operator-persona-name';
import { clearKairoVoiceFollowupWindow } from '../../lib/kairo-voice-followup-window';
import { useSpokenUtteranceText } from '../../composables/useSpokenUtteranceText';
import { formatVoiceGateFeedback } from '../../lib/kairo-voice-gate';
import { operatorExecutionStage } from '../../lib/operator-status-radar-view';
import { formatRunShortId } from '../../lib/run-display';
import { runContinueActionLabel } from '../../lib/run-lifecycle-ui';
import {
  dismissEmployeeSpecialtyRoute,
  undoEmployeeSpecialtyRoute,
} from '../../lib/apply-employee-specialty-route';
import { teammateRouteNotice } from '../../lib/teammate-route-notice';
import { useShellStore } from '../../stores/shell';
import {
  dismissVaxonBriefingInteraction,
  recordVaxonBriefingInteraction,
  vaxonBriefingInteractionKey,
  vaxonBriefingPendingByWorkspace,
} from '../../lib/vaxon-briefing-interaction';
import { vaxonAffirmReplyCta, vaxonLineAsksForReply } from '../../lib/vaxon-reply-prompt';
import VaxonConversationAttachControls from './VaxonConversationAttachControls.vue';

const shell = useShellStore();
const {
  draft,
  pending,
  thinkingLine,
  canSubmit,
  submitTurn,
  handleFocus,
  handleBlur,
  handleHistoryKeydown,
  speechCapture,
  attachments,
} = useKairoConversation();
const pendingAttachments = attachments.pendingAttachments;
const { spokenText, speaker } = useSpokenUtteranceText();

const workspaceId = computed(() => shell.currentWorkspace?.workspace_id ?? null);
const pendingDecision = computed(() => {
  const id = workspaceId.value?.trim();
  return id ? vaxonBriefingPendingByWorkspace.value[id] ?? null : null;
});
const pendingDecisionLine = computed(() => pendingDecision.value?.line.trim() ?? '');
const pendingDecisionCta = computed(() => vaxonAffirmReplyCta(pendingDecisionLine.value));

watch(
  () => [spokenText.value, speaker.value?.kind, speaker.value?.id] as const,
  ([line, kind, speakerId]) => {
    const text = line?.trim() ?? '';
    const id = workspaceId.value?.trim();
    if (!id || kind !== 'vaxon' || !vaxonLineAsksForReply(text)) {
      return;
    }
    recordVaxonBriefingInteraction({
      workspaceId: id,
      line: text,
      utteranceKey: vaxonBriefingInteractionKey(text, speakerId),
    });
  },
  { immediate: true },
);
const pendingApprovals = computed(
  () =>
    shell.operatorBriefing?.pending_approvals.count ??
    shell.runtimeSummary?.approvals.pending_count ??
    0,
);

const executionStage = computed(() =>
  operatorExecutionStage({
    workspaceId: workspaceId.value,
    runtimeSummary: shell.runtimeSummary,
    briefing: shell.operatorBriefing,
    loadState: shell.briefingLoadState,
    primaryActiveRun: shell.primaryActiveRun,
    workspaceReviewReadyCount: 0,
  }),
);

const showRunOrbit = computed(
  () =>
    executionStage.value.hasActiveRun ||
    shell.canCompletePrimaryRun ||
    shell.canResumePrimaryRun ||
    Boolean(shell.primaryActiveRun?.can_stop) ||
    pendingApprovals.value > 0,
);

const showStopAction = computed(
  () =>
    Boolean(shell.primaryActiveRun?.can_stop) ||
    shell.primaryActiveRun?.phase === 'executing',
);

const continueActionLabel = computed(() =>
  runContinueActionLabel({
    phase: shell.primaryActiveRun?.phase,
    agentStreamActive: shell.agentStreamActive,
    mode: shell.primaryActiveRun?.mode,
    pending: shell.runMutationState === 'resuming',
    continueLabel: 'Continue',
    resumeLabel: 'Resume',
    pendingLabel: 'Resuming…',
  }),
);

const inputPlaceholder = computed(() => {
  if (pending.value || kairoConversationPhase.value === 'thinking') {
    return `${OPERATOR_PERSONA_NAME} is checking — wait for the reply`;
  }
  if (speechCapture.interimTranscript.value) {
    return speechCapture.interimTranscript.value;
  }
  return `Ask ${OPERATOR_PERSONA_NAME} or dispatch a command… (Space hold-to-talk)`;
});

/** Block typing only while thinking/PTT — hands-free ambient listen must stay typeable. */
const inputDisabled = computed(
  () =>
    pending.value ||
    kairoConversationPhase.value === 'thinking' ||
    (speechCapture.capturing.value && speechCapture.captureMode.value === 'manual'),
);

async function undoTeammateRoute(): Promise<void> {
  await undoEmployeeSpecialtyRoute(shell, teammateRouteNotice.value);
}

function dismissTeammateRoute(): void {
  dismissEmployeeSpecialtyRoute();
}

function handleInputFocus(): void {
  handleFocus();
}

function handleInputKeydown(event: KeyboardEvent): void {
  const target = event.target;
  if (!(target instanceof HTMLInputElement)) {
    return;
  }
  handleHistoryKeydown(event, target);
}

const micDisabled = computed(
  () =>
    pending.value ||
    kairoConversationPhase.value === 'thinking' ||
    shell.operatorPresenceSettings.privacy_mode ||
    !speechCapture.supported,
);

const speechCaptureError = computed(
  () => speechCapture.captureError.value,
);

const voiceGateFeedback = computed(() =>
  formatVoiceGateFeedback(
    speechCapture.lastGateReason.value,
    speechCapture.lastHeardTranscript.value,
    speechCapture.lastAccepted.value,
  ),
);

const voiceDebugLine = computed(() => {
  const heard = speechCapture.lastHeardTranscript.value.trim();
  const reason = speechCapture.lastGateReason.value;
  const accepted = speechCapture.lastAccepted.value;
  const submitState = speechCapture.lastSubmitState.value;
  if (!heard && !reason && accepted === null && !submitState) {
    return '';
  }
  const parts = [];
  if (heard) {
    parts.push(`Heard: ${heard}`);
  }
  if (reason) {
    parts.push(`Gate: ${reason}`);
  }
  if (accepted !== null) {
    parts.push(`Accepted: ${accepted ? 'yes' : 'no'}`);
  }
  if (submitState) {
    parts.push(`Submit: ${submitState}`);
  }
  return parts.join(' · ');
});

const showInterrupt = computed(
  () => shell.kairoSpeechActive || kairoConversationPhase.value === 'thinking',
);

/** Floating Galaxy captions carry the spoken reply; keep the sticky Reply strip off the HUD. */
const showStickyReply = computed(
  () => Boolean(kairoConversationReply.value) && !shell.operatorBrainGalaxyActive,
);

/** Gate rejection copy stays useful; the verbose Heard/Accepted debug line does not on Galaxy. */
const showVoiceDebugLine = computed(
  () => Boolean(voiceDebugLine.value) && !shell.operatorBrainGalaxyActive,
);

function handleInterrupt(): void {
  shell.interruptKairoVoice();
  clearKairoVoiceFollowupWindow();
  setKairoConversationPhase('idle');
}

function handleEscapeHotkey(event: KeyboardEvent): void {
  if (event.key !== 'Escape' || !showInterrupt.value) {
    return;
  }
  event.preventDefault();
  handleInterrupt();
}

const micTitle = computed(() => {
  if (shell.operatorPresenceSettings.privacy_mode) {
    return 'Voice blocked in privacy mode';
  }
  if (!speechCapture.supported) {
    return 'Speech recognition unavailable in this browser';
  }
  return 'Hold to talk';
});

async function handleSubmit(): Promise<void> {
  await submitTurn();
}

async function replyToPendingDecision(reply: 'yes' | 'not now'): Promise<void> {
  const id = workspaceId.value?.trim();
  if (!id || pending.value) {
    return;
  }
  dismissVaxonBriefingInteraction(id);
  await submitTurn(reply);
}

function dismissPendingDecision(): void {
  const id = workspaceId.value?.trim();
  if (id) {
    dismissVaxonBriefingInteraction(id);
  }
}

function startManualPtt(): boolean {
  if (micDisabled.value) {
    return false;
  }
  shell.interruptKairoVoice();
  // Takeover so Space works while hands-free ambient capture is already open.
  return speechCapture.startCapture('manual', { takeover: true });
}

function handleMicPointerDown(event: PointerEvent): void {
  if (micDisabled.value) {
    return;
  }
  const target = event.currentTarget;
  if (target instanceof HTMLElement && target.setPointerCapture) {
    target.setPointerCapture(event.pointerId);
  }
  startManualPtt();
}

function handleMicPointerUp(event: PointerEvent): void {
  const target = event.currentTarget;
  if (target instanceof HTMLElement && target.releasePointerCapture) {
    try {
      if (target.hasPointerCapture(event.pointerId)) {
        target.releasePointerCapture(event.pointerId);
      }
    } catch {
      // Pointer may already be released if the browser disabled the control mid-gesture.
    }
  }
  if (speechCapture.capturing.value && speechCapture.captureMode.value === 'manual') {
    speechCapture.stopCapture();
  }
}

function isConversationBarPttInput(target: EventTarget | null): boolean {
  return (
    target instanceof HTMLElement &&
    target.matches('input.kairo-conversation-bar__input[data-kairo-ptt-input]')
  );
}

function handleSpaceHotkey(event: KeyboardEvent): void {
  if (event.code !== 'Space' || event.repeat) {
    return;
  }
  const target = event.target;
  if (
    target instanceof HTMLElement &&
    (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.isContentEditable)
  ) {
    // Allow Space PTT when the command bar is focused and empty (common case).
    if (!isConversationBarPttInput(target) || draft.value.trim().length > 0) {
      return;
    }
  }
  if (!shell.operatorBrainGalaxyActive || shell.layoutMode !== 'operator') {
    return;
  }
  if (pending.value || kairoConversationPhase.value === 'thinking') {
    return;
  }
  if (micDisabled.value) {
    return;
  }
  // Already in a Space/Mic hold — ignore repeat keydown until release.
  if (speechCapture.capturing.value && speechCapture.captureMode.value === 'manual') {
    event.preventDefault();
    return;
  }
  event.preventDefault();
  startManualPtt();
}

function handleSpaceKeyup(event: KeyboardEvent): void {
  if (event.code !== 'Space') {
    return;
  }
  if (speechCapture.capturing.value && speechCapture.captureMode.value === 'manual') {
    speechCapture.stopCapture();
  }
}

let unregisterSubmit: (() => void) | null = null;

onMounted(() => {
  window.addEventListener('keydown', handleSpaceHotkey);
  window.addEventListener('keyup', handleSpaceKeyup);
  window.addEventListener('keydown', handleEscapeHotkey);
  unregisterSubmit = registerKairoConversationSubmit(submitTurn);
});

onUnmounted(() => {
  window.removeEventListener('keydown', handleSpaceHotkey);
  window.removeEventListener('keyup', handleSpaceKeyup);
  window.removeEventListener('keydown', handleEscapeHotkey);
  unregisterSubmit?.();
});
</script>

<template>
  <div
    class="kairo-conversation-bar"
    :class="{ 'kairo-conversation-bar--busy': pending || kairoConversationPhase === 'thinking' }"
  >
    <AgentDockTeammateRouteBanner
      :show="Boolean(teammateRouteNotice)"
      :to-name="teammateRouteNotice?.toName ?? ''"
      :role-label="teammateRouteNotice?.toRoleLabel"
      :from-name="teammateRouteNotice?.fromName"
      @undo="undoTeammateRoute"
      @dismiss="dismissTeammateRoute"
    />
    <VaxonConversationAttachControls
      v-if="pendingAttachments.length"
      chips-only
      :attachments="pendingAttachments"
      :disabled="inputDisabled"
      @attach="attachments.pickFiles"
      @remove="attachments.removeAttachment"
    />
    <div class="kairo-conversation-bar__command-row">
      <form
        class="kairo-conversation-bar__form"
        @submit.prevent="handleSubmit"
        @paste="attachments.handlePaste"
        @dragover.prevent
        @drop.prevent="attachments.handleDrop"
      >
        <span class="kairo-conversation-bar__glyph-slot" aria-hidden="true">
          <OperatorPersonaMark size="xs" />
        </span>
        <input
          v-model="draft"
          class="kairo-conversation-bar__input"
          type="text"
          data-kairo-ptt-input
          autocomplete="off"
          spellcheck="false"
          :placeholder="inputPlaceholder"
          :disabled="inputDisabled"
          @focus="handleInputFocus"
          @blur="handleBlur"
          @keydown="handleInputKeydown"
        />
        <VaxonConversationAttachControls
          button-only
          :attachments="pendingAttachments"
          :disabled="inputDisabled"
          @attach="attachments.pickFiles"
          @remove="attachments.removeAttachment"
        />
        <button
          v-if="showInterrupt"
          type="button"
          class="kairo-conversation-bar__interrupt"
          :title="`Stop ${OPERATOR_PERSONA_NAME} (Esc)`"
          :aria-label="`Interrupt ${OPERATOR_PERSONA_NAME}`"
          @click="handleInterrupt"
        >
          Interrupt
        </button>
        <button
          type="button"
          class="kairo-conversation-bar__mic"
          :class="{
            'kairo-conversation-bar__mic--active':
              speechCapture.capturing.value && speechCapture.captureMode.value === 'manual',
          }"
          :disabled="micDisabled"
          :title="micTitle"
          aria-label="Hold to talk"
          @pointerdown.prevent="handleMicPointerDown"
          @pointerup.prevent="handleMicPointerUp"
          @pointercancel.prevent="handleMicPointerUp"
          @pointerleave="handleMicPointerUp"
        >
          {{
            speechCapture.capturing.value && speechCapture.captureMode.value === 'manual'
              ? 'Listening…'
              : speechCapture.capturing.value
                ? 'Armed'
                : 'Mic'
          }}
        </button>
        <button type="submit" class="kairo-conversation-bar__send" :disabled="!canSubmit">
          Send
        </button>
      </form>

      <div v-if="showRunOrbit" class="kairo-conversation-bar__run-orbit">
        <span v-if="executionStage.hasActiveRun" class="brain-galaxy-stage__run-phase">
          {{ executionStage.phase }}
        </span>
        <span v-if="shell.primaryActiveRun" class="brain-galaxy-stage__run-id">
          #{{ formatRunShortId(shell.primaryActiveRun.run_id) }}
        </span>
        <button
          v-if="showStopAction"
          type="button"
          class="brain-galaxy-stage__run-btn brain-galaxy-stage__run-btn--stop"
          :disabled="!shell.canStopPrimaryRun && shell.primaryActiveRun?.phase !== 'executing'"
          @click="shell.stopPrimaryRun()"
        >
          Stop
        </button>
        <button
          v-if="shell.canResumePrimaryRun"
          type="button"
          class="brain-galaxy-stage__run-btn brain-galaxy-stage__run-btn--warn"
          :disabled="shell.runMutationPending"
          @click="shell.resumePrimaryRun()"
        >
          {{ continueActionLabel }}
        </button>
        <button
          v-if="shell.canCompletePrimaryRun"
          type="button"
          class="brain-galaxy-stage__run-btn"
          :disabled="shell.runMutationPending"
          @click="shell.completePrimaryRun()"
        >
          Complete
        </button>
        <button
          v-if="pendingApprovals > 0"
          type="button"
          class="brain-galaxy-stage__run-btn brain-galaxy-stage__run-btn--warn"
          @click="shell.focusAttentionSidebar()"
        >
          Attention · {{ pendingApprovals }}
        </button>
      </div>
    </div>

    <p v-if="speechCapture.interimTranscript" class="kairo-conversation-bar__interim">
      {{ speechCapture.interimTranscript }}
    </p>
    <p
      v-else-if="pending && thinkingLine"
      class="kairo-conversation-bar__interim kairo-conversation-bar__interim--thinking"
    >
      {{ thinkingLine }}
    </p>
    <p
      v-else-if="voiceGateFeedback"
      class="kairo-conversation-bar__interim kairo-conversation-bar__interim--gate"
      role="status"
    >
      {{ voiceGateFeedback }}
    </p>
    <section
      v-if="pendingDecisionLine"
      class="kairo-conversation-bar__decision"
      aria-label="VAXON decision required"
    >
      <div>
        <p class="kairo-conversation-bar__decision-label">VAXON is waiting for your decision</p>
        <p class="kairo-conversation-bar__decision-copy">{{ pendingDecisionLine }}</p>
      </div>
      <div class="kairo-conversation-bar__decision-actions">
        <button
          type="button"
          class="kairo-conversation-bar__decision-affirm"
          :disabled="pending"
          @click="replyToPendingDecision('yes')"
        >
          {{ pendingDecisionCta }}
        </button>
        <button
          type="button"
          class="kairo-conversation-bar__decision-decline"
          :disabled="pending"
          @click="replyToPendingDecision('not now')"
        >
          Not now
        </button>
        <button
          type="button"
          class="kairo-conversation-bar__decision-dismiss"
          :disabled="pending"
          aria-label="Dismiss VAXON decision"
          @click="dismissPendingDecision"
        >
          Dismiss
        </button>
      </div>
    </section>
    <div v-if="showStickyReply" class="kairo-conversation-bar__reply">
      <span class="kairo-conversation-bar__reply-heading">
        <OperatorPersonaMark size="xs" />
        <span class="kairo-conversation-bar__reply-label">Reply</span>
      </span>
      <p class="kairo-conversation-bar__reply-text">{{ kairoConversationReply }}</p>
    </div>
    <p v-if="speechCaptureError" class="kairo-conversation-bar__error" role="alert">
      {{ speechCaptureError }}
    </p>
    <p v-if="showVoiceDebugLine" class="kairo-conversation-bar__interim kairo-conversation-bar__interim--debug">
      {{ voiceDebugLine }}
    </p>
    <p v-if="kairoConversationError" class="kairo-conversation-bar__error" role="alert">
      {{ kairoConversationError }}
    </p>
  </div>
</template>
