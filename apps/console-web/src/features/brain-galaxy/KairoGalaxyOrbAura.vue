<script setup lang="ts">
/**
 * Orb satellite aura disabled for movie-JARVIS minimal chrome.
 * Presence is conveyed by orb glow/spin classes, not floating text chips.
 */
</script>

<template>
  <div class="kairo-orb-aura kairo-orb-aura--silent" aria-hidden="true" />
</template>

<style scoped>
.kairo-orb-aura--silent {
  display: none;
}
</style>
