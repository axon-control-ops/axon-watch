<script setup lang="ts">
import { computed } from 'vue';

import {
  kairoConversationError,
  kairoConversationPhase,
  kairoConversationReply,
} from '../../features/kairo-conversation/kairo-conversation-state';
import { useKairoConversation } from '../../features/kairo-conversation/use-kairo-conversation';
import { useShellStore } from '../../stores/shell';

const shell = useShellStore();
const { draft, pending, canSubmit, submitTurn, handleFocus, handleBlur, speechCapture, startVoiceCapture, stopVoiceCapture } =
  useKairoConversation();

const showStopSpeech = computed(() => shell.kairoSpeechActive);
const showStopRun = computed(() => shell.canStopIdeAgentRun);

async function handleSubmit(): Promise<void> {
  await submitTurn();
}

function handleStopSpeech(): void {
  shell.stopKairoSpeech();
}

function handleStopRun(): void {
  void shell.stopIdeAgentRun();
}

function toggleVoiceCapture(): void {
  if (speechCapture.capturing.value) {
    stopVoiceCapture();
    return;
  }
  startVoiceCapture();
}
</script>

<template>
  <section class="ide-kairo-conversation" aria-label="KAIRO conversation">
    <form class="kairo-conversation-bar__form ide-kairo-conversation__form" @submit.prevent="handleSubmit">
      <span class="kairo-conversation-bar__glyph" aria-hidden="true">◎</span>
      <input
        v-model="draft"
        class="kairo-conversation-bar__input"
        type="text"
        autocomplete="off"
        spellcheck="false"
        placeholder="Talk to KAIRO — answers are spoken aloud"
        :disabled="pending"
        @focus="handleFocus"
        @blur="handleBlur"
      />
      <button
        v-if="speechCapture.supported"
        type="button"
        class="kairo-conversation-bar__mic"
        :class="{ 'is-active': speechCapture.capturing.value }"
        :disabled="shell.operatorPresenceSettings.privacy_mode"
        :title="speechCapture.capturing.value ? 'Stop listening' : 'Speak to KAIRO (interrupts playback)'"
        @click="toggleVoiceCapture"
      >
        {{ speechCapture.capturing.value ? 'Listening…' : 'Mic' }}
      </button>
      <button
        v-if="showStopSpeech"
        type="button"
        class="ide-kairo-conversation__interrupt"
        @click="handleStopSpeech"
      >
        Stop speaking
      </button>
      <button
        v-else-if="showStopRun"
        type="button"
        class="ide-kairo-conversation__interrupt ide-kairo-conversation__interrupt--run"
        :disabled="shell.runMutationState === 'stopping'"
        @click="handleStopRun"
      >
        Stop run
      </button>
      <button type="submit" class="kairo-conversation-bar__send" :disabled="!canSubmit">
        Ask
      </button>
    </form>

    <p v-if="kairoConversationReply" class="kairo-conversation-bar__reply">
      <strong>KAIRO</strong>
      <span>{{ kairoConversationReply }}</span>
    </p>
    <p v-if="kairoConversationError" class="kairo-conversation-bar__error" role="alert">
      {{ kairoConversationError }}
    </p>
    <p v-else-if="kairoConversationPhase === 'thinking'" class="ide-kairo-conversation__hint">
      Thinking…
    </p>
    <p v-else class="ide-kairo-conversation__hint">
      Esc or tap KAIRO to interrupt speech · Mic barge-in stops playback
    </p>
  </section>
</template>

<style scoped>
.ide-kairo-conversation {
  display: grid;
  gap: 0.35rem;
  padding: 0.45rem 0.55rem 0;
  border-top: 1px solid rgba(99, 102, 241, 0.18);
}

.ide-kairo-conversation__form {
  width: 100%;
}

.ide-kairo-conversation__interrupt {
  border: 1px solid rgba(255, 140, 120, 0.42);
  border-radius: 0.35rem;
  background: rgba(255, 120, 72, 0.12);
  color: rgba(255, 210, 190, 0.96);
  cursor: pointer;
  font: inherit;
  font-size: 0.68rem;
  padding: 0.28rem 0.5rem;
  white-space: nowrap;
}

.ide-kairo-conversation__interrupt--run {
  border-color: rgba(255, 196, 72, 0.42);
  background: rgba(255, 196, 72, 0.12);
  color: rgba(255, 236, 190, 0.96);
}

.ide-kairo-conversation__hint {
  margin: 0;
  font-size: 0.62rem;
  color: rgba(138, 154, 173, 0.82);
}
</style>
