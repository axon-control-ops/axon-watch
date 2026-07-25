<script setup lang="ts">
import type { DebugReproduceRequest } from '../../../lib/debug-reproduce-view';

const props = defineProps<{
  request: DebugReproduceRequest;
  pending: boolean;
}>();

const emit = defineEmits<{
  proceed: [];
  dismiss: [];
}>();
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
