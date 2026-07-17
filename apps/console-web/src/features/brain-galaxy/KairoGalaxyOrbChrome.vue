<script setup lang="ts">
defineProps<{
  personaName: string;
  orbStatusLabel: string;
  modeLabel: string;
  ttsBadge?: string;
  showInterrupt: boolean;
  hint: string;
  modelLabel: string;
}>();

const emit = defineEmits<{
  interrupt: [];
  focusBriefing: [];
}>();
</script>

<template>
  <div class="kairo-galaxy-orb__chrome">
    <div class="kairo-galaxy-orb__status">
      <span class="kairo-galaxy-orb__status-dot" aria-hidden="true" />
      <span class="kairo-galaxy-orb__status-label">{{ orbStatusLabel }}</span>
    </div>
    <p v-if="modeLabel" class="kairo-galaxy-orb__mode-pill">{{ modeLabel }}</p>
    <p v-if="ttsBadge" class="kairo-galaxy-orb__tts-badge">{{ ttsBadge }}</p>
    <button
      v-if="showInterrupt"
      type="button"
      class="kairo-galaxy-orb__interrupt"
      :title="`Stop ${personaName} (Esc)`"
      :aria-label="`Interrupt ${personaName}`"
      @click.stop="emit('interrupt')"
    >
      Interrupt
    </button>
    <p class="kairo-galaxy-orb__hint">{{ hint }}</p>
    <button
      type="button"
      class="kairo-galaxy-orb__model"
      @pointerdown.stop
      @click="emit('focusBriefing')"
    >
      <span aria-hidden="true">◆</span>
      {{ modelLabel }}
    </button>
  </div>
</template>
