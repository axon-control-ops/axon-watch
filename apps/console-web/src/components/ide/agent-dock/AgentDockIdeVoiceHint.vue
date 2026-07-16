<script setup lang="ts">
defineProps<{
  message: string;
}>();

const emit = defineEmits<{
  dismiss: [];
}>();
</script>

<template>
  <div class="agent-dock-ide-voice-hint" role="status">
    <p class="agent-dock-ide-voice-hint__copy">{{ message }}</p>
    <button type="button" class="agent-dock-ide-voice-hint__dismiss" @click="emit('dismiss')">
      Dismiss
    </button>
  </div>
</template>

<style scoped>
.agent-dock-ide-voice-hint {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin: 0 0 8px;
  padding: 10px 12px;
  border: 1px solid color-mix(in srgb, var(--cursor-border) 70%, transparent);
  border-radius: 8px;
  background: color-mix(in srgb, var(--cursor-panel-bg) 92%, var(--cursor-accent) 8%);
}

.agent-dock-ide-voice-hint__copy {
  margin: 0;
  font-size: 12px;
  line-height: 1.45;
  color: var(--cursor-fg-muted);
}

.agent-dock-ide-voice-hint__dismiss {
  flex: 0 0 auto;
  border: 0;
  background: transparent;
  color: var(--cursor-fg);
  font-size: 12px;
  cursor: pointer;
  text-decoration: underline;
}
</style>
