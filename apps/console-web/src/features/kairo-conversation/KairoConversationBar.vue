<script setup lang="ts">
import { computed, onMounted, onUnmounted } from 'vue';

import {
  kairoConversationError,
  kairoConversationReply,
} from './kairo-conversation-state';
import { useKairoConversation } from './use-kairo-conversation';
import { registerKairoConversationSubmit } from './kairo-conversation-bus';
import { operatorExecutionStage } from '../../lib/operator-status-radar-view';
import { formatRunShortId } from '../../lib/run-display';
import { useShellStore } from '../../stores/shell';

const shell = useShellStore();
const { draft, pending, canSubmit, submitTurn, handleFocus, handleBlur, speechCapture } =
  useKairoConversation();

const workspaceId = computed(() => shell.currentWorkspace?.workspace_id ?? null);
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
    Boolean(shell.primaryActiveRun?.can_stop) ||
    pendingApprovals.value > 0,
);

const showStopAction = computed(
  () =>
    Boolean(shell.primaryActiveRun?.can_stop) ||
    shell.primaryActiveRun?.phase === 'executing',
);

const inputPlaceholder = computed(() => {
  if (speechCapture.interimTranscript.value) {
    return speechCapture.interimTranscript.value;
  }
  return 'Ask KAIRO or dispatch a command… (Space hold-to-talk)';
});

const micDisabled = computed(
  () =>
    pending.value ||
    speechCapture.capturing.value ||
    shell.operatorPresenceSettings.privacy_mode ||
    !speechCapture.supported,
);

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

function handleMicPointerDown(): void {
  if (micDisabled.value) {
    return;
  }
  speechCapture.startCapture();
}

function handleMicPointerUp(): void {
  if (speechCapture.capturing.value) {
    speechCapture.stopCapture();
  }
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
    return;
  }
  if (!shell.operatorBrainGalaxyActive || shell.layoutMode !== 'operator') {
    return;
  }
  event.preventDefault();
  if (speechCapture.capturing.value) {
    speechCapture.stopCapture();
  } else if (speechCapture.canCapture()) {
    speechCapture.startCapture();
  }
}

function handleSpaceKeyup(event: KeyboardEvent): void {
  if (event.code !== 'Space') {
    return;
  }
  if (speechCapture.capturing.value) {
    speechCapture.stopCapture();
  }
}

let unregisterSubmit: (() => void) | null = null;

onMounted(() => {
  window.addEventListener('keydown', handleSpaceHotkey);
  window.addEventListener('keyup', handleSpaceKeyup);
  unregisterSubmit = registerKairoConversationSubmit(submitTurn);
});

onUnmounted(() => {
  window.removeEventListener('keydown', handleSpaceHotkey);
  window.removeEventListener('keyup', handleSpaceKeyup);
  unregisterSubmit?.();
});
</script>

<template>
  <div class="kairo-conversation-bar">
    <form class="kairo-conversation-bar__form" @submit.prevent="handleSubmit">
      <span class="kairo-conversation-bar__glyph" aria-hidden="true">◎</span>
      <input
        v-model="draft"
        class="kairo-conversation-bar__input"
        type="text"
        autocomplete="off"
        spellcheck="false"
        :placeholder="inputPlaceholder"
        :disabled="pending || speechCapture.capturing.value"
        @focus="handleFocus"
        @blur="handleBlur"
      />
      <button
        type="button"
        class="kairo-conversation-bar__mic"
        :class="{ 'kairo-conversation-bar__mic--active': speechCapture.capturing.value }"
        :disabled="micDisabled"
        :title="micTitle"
        aria-label="Hold to talk"
        @pointerdown.prevent="handleMicPointerDown"
        @pointerup.prevent="handleMicPointerUp"
        @pointerleave="handleMicPointerUp"
      >
        Mic
      </button>
      <button type="submit" class="kairo-conversation-bar__send" :disabled="!canSubmit">
        Send
      </button>
    </form>

    <p v-if="speechCapture.interimTranscript" class="kairo-conversation-bar__interim">
      {{ speechCapture.interimTranscript }}
    </p>
    <p v-if="kairoConversationReply" class="kairo-conversation-bar__reply">
      <strong>KAIRO</strong>
      <span>{{ kairoConversationReply }}</span>
    </p>
    <p v-if="kairoConversationError" class="kairo-conversation-bar__error" role="alert">
      {{ kairoConversationError }}
    </p>

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
</template>
