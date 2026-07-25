<script setup lang="ts">
const props = defineProps<{
  show: boolean;
  reasonLabel?: string;
  /** 'switched' = already flipped; 'offer' = Cursor-like pause before submit. */
  kind?: 'switched' | 'offer';
}>();

const emit = defineEmits<{
  undo: [];
  dismiss: [];
  acceptOffer: [];
  declineOffer: [];
}>();
</script>

<template>
  <div
    v-if="show"
    class="agent-dock-composer__plan-switch-banner"
    role="status"
  >
    <p
      v-if="kind === 'offer'"
      class="agent-dock-composer__plan-switch-copy"
    >
      Plan recommended{{ reasonLabel ? ` (${reasonLabel})` : '' }} — review approach first?
      <button
        type="button"
        class="agent-dock-composer__plan-switch-btn"
        @click="emit('acceptOffer')"
      >
        Use Plan
      </button>
      ·
      <button
        type="button"
        class="agent-dock-composer__plan-switch-btn"
        @click="emit('declineOffer')"
      >
        Stay in Agent
      </button>
    </p>
    <p
      v-else
      class="agent-dock-composer__plan-switch-copy"
    >
      Switched to Plan for this turn{{ reasonLabel ? ` (${reasonLabel})` : '' }} —
      <button
        type="button"
        class="agent-dock-composer__plan-switch-btn"
        @click="emit('undo')"
      >
        Undo
      </button>
    </p>
    <button
      type="button"
      class="agent-dock-composer__plan-switch-btn"
      :aria-label="kind === 'offer' ? 'Cancel plan offer' : 'Dismiss plan switch notice'"
      @click="emit('dismiss')"
    >
      Dismiss
    </button>
  </div>
</template>
