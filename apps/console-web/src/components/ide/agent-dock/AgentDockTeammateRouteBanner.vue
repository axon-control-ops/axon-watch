<script setup lang="ts">
defineProps<{
  show: boolean;
  toName: string;
  roleLabel?: string;
  fromName?: string;
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
      Routed to {{ toName }}{{ roleLabel ? ` (${roleLabel})` : '' }}{{ fromName ? ` from ${fromName}` : '' }} —
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
      aria-label="Dismiss teammate route notice"
      @click="emit('dismiss')"
    >
      Dismiss
    </button>
  </div>
</template>
