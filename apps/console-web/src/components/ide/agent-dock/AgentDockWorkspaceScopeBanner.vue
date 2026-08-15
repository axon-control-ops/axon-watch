<script setup lang="ts">
defineProps<{
  show: boolean;
  inferredLabel: string;
  currentLabel: string;
  pending?: boolean;
}>();

const emit = defineEmits<{
  switchWorkspace: [];
  dismiss: [stayHere?: boolean];
}>();
</script>

<template>
  <div
    v-if="show"
    class="agent-dock-composer__plan-switch-banner agent-dock-composer__plan-switch-banner--workspace-scope"
    role="alert"
  >
    <p class="agent-dock-composer__plan-switch-copy">
      {{ inferredLabel }} work detected while you are in {{ currentLabel }} —
      <button
        type="button"
        class="agent-dock-composer__plan-switch-btn"
        :disabled="pending"
        @click="emit('switchWorkspace')"
      >
        Switch to {{ inferredLabel }}
      </button>
    </p>
    <button
      type="button"
      class="agent-dock-composer__plan-switch-btn"
      :aria-label="`Stay in ${currentLabel} and stop asking`"
      @click="emit('dismiss', true)"
    >
      No — continue here
    </button>
    <button
      type="button"
      class="agent-dock-composer__plan-switch-btn"
      aria-label="Dismiss workspace scope notice"
      @click="emit('dismiss')"
    >
      Dismiss
    </button>
  </div>
</template>
