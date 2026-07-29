<script setup lang="ts">
import OperatorPersonaMark from '../../OperatorPersonaMark.vue';

defineProps<{
  composerMode: string;
  operatorPersonaName: string;
  kairoConversationReply: string | null;
  kairoConversationError: string | null;
  commandMutationError: string | null;
  runMutationError: string | null;
  workspaceSelected: boolean;
}>();
</script>

<template>
  <div v-if="composerMode === 'kairo' && kairoConversationReply" class="agent-dock-composer__kairo-reply">
    <span class="agent-dock-composer__kairo-reply-label">
      <OperatorPersonaMark size="xs" />
      <span>Reply</span>
    </span>
    <p class="agent-dock-composer__kairo-reply-text">{{ kairoConversationReply }}</p>
  </div>
  <div
    v-if="composerMode === 'kairo' && kairoConversationError"
    class="agent-dock-notice agent-dock-notice--error"
    role="alert"
  >
    <span class="agent-dock-notice__rail" aria-hidden="true" />
    <p class="agent-dock-notice__copy">{{ kairoConversationError }}</p>
  </div>
  <p v-else-if="composerMode === 'kairo'" class="agent-dock-composer__kairo-hint">
    Tap header {{ operatorPersonaName }} to pause or continue · Esc stops speech · Mic barge-in
  </p>
  <p v-if="!workspaceSelected" class="agent-dock-composer__empty">Select a workspace to send commands.</p>
  <div
    v-if="commandMutationError"
    class="agent-dock-notice agent-dock-notice--error"
    role="alert"
  >
    <span class="agent-dock-notice__rail" aria-hidden="true" />
    <p class="agent-dock-notice__copy">{{ commandMutationError }}</p>
  </div>
  <div
    v-if="runMutationError"
    class="agent-dock-notice agent-dock-notice--error"
    role="alert"
  >
    <span class="agent-dock-notice__rail" aria-hidden="true" />
    <p class="agent-dock-notice__copy">{{ runMutationError }}</p>
  </div>
</template>
