<script setup lang="ts">
defineProps<{
  title: string;
  hero?: boolean;
  seamClass?: string;
}>();
</script>

<template>
  <section
    class="hud-seam"
    :class="[seamClass, { 'hud-seam--hero': hero }]"
  >
    <span class="hud-seam__corner hud-seam__corner--tl" aria-hidden="true" />
    <span class="hud-seam__corner hud-seam__corner--tr" aria-hidden="true" />
    <span class="hud-seam__corner hud-seam__corner--bl" aria-hidden="true" />
    <span class="hud-seam__corner hud-seam__corner--br" aria-hidden="true" />

    <p class="hud-seam__title">{{ title }}</p>
    <div class="hud-seam__body">
      <slot />
    </div>
  </section>
</template>
