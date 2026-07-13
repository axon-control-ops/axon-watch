<script setup lang="ts">
import { onMounted, watch } from 'vue';

import { axonDebugSessionLog } from '../../../lib/axon-debug-session-log';
import type { DebugReproduceRequest } from '../../../lib/debug-reproduce-view';
import { isKairoVoiceSpeaking } from '../../../lib/kairo-voice-playback';
import { kairoConversationPhase } from '../../../features/kairo-conversation/kairo-conversation-state';

const props = defineProps<{
  request: DebugReproduceRequest;
  pending: boolean;
}>();

const emit = defineEmits<{
  proceed: [];
  dismiss: [];
}>();

function logBannerVoiceState(reason: string): void {
  // #region agent log
  axonDebugSessionLog({
    hypothesisId: 'H3',
    location: 'AgentDockDebugReproduceBanner.vue',
    message: reason,
    data: {
      stepCount: props.request.steps.length,
      stepsPreview: props.request.steps.slice(0, 3),
      pending: props.pending,
      conversationPhase: kairoConversationPhase.value,
      voiceSpeaking: isKairoVoiceSpeaking(),
    },
  });
  // #endregion
}

onMounted(() => {
  logBannerVoiceState('debug reproduce banner mounted');
});

watch(
  () => kairoConversationPhase.value,
  (phase) => {
    logBannerVoiceState(`phase while banner visible: ${phase}`);
  },
);
</script>

<template>
  <div class="agent-dock-composer__debug-reproduce-banner" role="status">
    <p class="agent-dock-composer__debug-reproduce-copy">
      Reproduce the bug with these steps, then proceed so Debug can read runtime logs and continue.
    </p>
    <ol class="agent-dock-composer__debug-reproduce-steps">
      <li v-for="(step, index) in request.steps" :key="index">{{ step }}</li>
    </ol>
    <div class="agent-dock-composer__debug-reproduce-actions">
      <button
        type="button"
        class="agent-dock-composer__debug-reproduce-btn agent-dock-composer__debug-reproduce-btn--proceed"
        :disabled="pending"
        @click="emit('proceed')"
      >
        {{ pending ? 'Sending…' : 'Proceed — bug reproduced' }}
      </button>
      <button
        type="button"
        class="agent-dock-composer__debug-reproduce-btn agent-dock-composer__debug-reproduce-btn--dismiss"
        :disabled="pending"
        @click="emit('dismiss')"
      >
        Dismiss
      </button>
    </div>
  </div>
</template>
