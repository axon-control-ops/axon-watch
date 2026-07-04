<script setup lang="ts">
withDefaults(
  defineProps<{
    size?: number;
  }>(),
  { size: 12 },
);
</script>

<template>
  <span class="briefing-seam-icon" aria-hidden="true">
    <svg
      class="briefing-seam-icon__svg"
      :width="size"
      :height="size"
      viewBox="0 0 16 16"
      fill="none"
    >
      <path
        d="M8 8.1 4.4 5.2M8 8.1 11.6 5.2M8 8.1 5.4 11.4M8 8.1 10.6 11.1"
        stroke="currentColor"
        stroke-width="0.65"
        stroke-linecap="round"
        opacity="0.55"
      />
      <circle cx="4.4" cy="5.2" r="0.95" fill="currentColor" opacity="0.78" />
      <circle cx="11.6" cy="5.2" r="0.95" fill="currentColor" opacity="0.78" />
      <circle cx="5.4" cy="11.4" r="0.82" fill="currentColor" opacity="0.68" />
      <circle cx="10.6" cy="11.1" r="0.82" fill="currentColor" opacity="0.68" />
      <circle cx="8" cy="8.1" r="1.35" fill="currentColor" />
    </svg>
  </span>
</template>
