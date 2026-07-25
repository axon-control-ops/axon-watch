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
  <p v-if="composerMode === 'kairo' && kairoConversationError" class="agent-dock-composer__error" role="alert">
    {{ kairoConversationError }}
  </p>
  <p v-else-if="composerMode === 'kairo'" class="agent-dock-composer__kairo-hint">
    Tap header {{ operatorPersonaName }} to pause or continue · Esc stops speech · Mic barge-in
  </p>
  <p v-if="!workspaceSelected" class="agent-dock-composer__empty">Select a workspace to send commands.</p>
  <p v-if="commandMutationError" class="agent-dock-composer__error">
    {{ commandMutationError }}
  </p>
  <p v-if="runMutationError" class="agent-dock-composer__error">
    {{ runMutationError }}
  </p>
</template>
