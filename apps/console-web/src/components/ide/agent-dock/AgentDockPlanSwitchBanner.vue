<script setup lang="ts">
defineProps<{
  show: boolean;
  reasonLabel?: string;
}>();

const emit = defineEmits<{
  undo: [];
  dismiss: [];
}>();
</script>

<template>
  <div
    v-if="show"
    class="agent-dock-composer__plan-switch-banner"
    role="status"
  >
    <p class="agent-dock-composer__plan-switch-copy">
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
      aria-label="Dismiss plan switch notice"
      @click="emit('dismiss')"
    >
      Dismiss
    </button>
  </div>
</template>
