<script setup lang="ts">
defineProps<{
  text: string;
}>();
</script>

<template>
  <div class="agent-dock-sticky-prompt" role="status" aria-live="polite">
    <span class="agent-dock-sticky-prompt__label">You</span>
    <p class="agent-dock-sticky-prompt__text">{{ text }}</p>
  </div>
</template>
