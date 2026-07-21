<script setup lang="ts">
defineProps<{
  personaName: string;
  /** Kept for API stability; movie mode hides status/mode/tts/hint/model text. */
  orbStatusLabel?: string;
  modeLabel?: string;
  ttsBadge?: string;
  showInterrupt: boolean;
  hint?: string;
  modelLabel?: string;
}>();

const emit = defineEmits<{
  interrupt: [];
  focusBriefing: [];
}>();
</script>

<template>
  <!-- Movie-JARVIS: almost no chrome text — speaking is orb glow/spin only. -->
  <div class="kairo-galaxy-orb__chrome kairo-galaxy-orb__chrome--minimal">
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
  </div>
</template>
