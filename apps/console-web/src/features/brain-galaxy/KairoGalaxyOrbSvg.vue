<script setup lang="ts">
/**
 * Cinematic VAXON orb face — stock JARVIS-style illustration as the primary
 * visual, with thin animated HUD overlays for continuous presence.
 */
defineProps<{
  /** Kept for host API compatibility; branding lives in the illustration. */
  personaOrbLabel?: string;
}>();

const cinematicSrc = '/vaxon-orb-cinematic.png';
</script>

<template>
  <div class="kairo-galaxy-orb__cinematic" aria-hidden="true">
    <img
      class="kairo-galaxy-orb__cinematic-art"
      :src="cinematicSrc"
      alt=""
      draggable="false"
    />
    <div class="kairo-galaxy-orb__cinematic-spin" aria-hidden="true" />
    <div class="kairo-galaxy-orb__cinematic-spin kairo-galaxy-orb__cinematic-spin--counter" aria-hidden="true" />
    <div class="kairo-galaxy-orb__cinematic-pulse" aria-hidden="true" />
    <div class="kairo-galaxy-orb__cinematic-scan" aria-hidden="true" />
  </div>
</template>
