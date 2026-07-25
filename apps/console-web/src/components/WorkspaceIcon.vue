<script setup lang="ts">
withDefaults(
  defineProps<{
    kind: string;
    size?: number;
  }>(),
  { size: 16 },
);
</script>

<template>
  <svg
    class="workspace-icon"
    :width="size"
    :height="size"
    viewBox="0 0 16 16"
    fill="none"
    stroke="currentColor"
    stroke-width="1.05"
    stroke-linecap="round"
    stroke-linejoin="round"
    aria-hidden="true"
  >
    <template v-if="kind === 'cube' || kind === 'chart'">
      <path d="M8 2.5 12.5 5v5L8 12.5 3.5 10V5z" />
      <path d="M8 2.5v5M3.5 5 8 7.5 12.5 5" />
    </template>
    <template v-else-if="kind === 'building'">
      <path d="M3.5 13.5V5.5l4.5-2.5 4.5 2.5v8" />
      <path d="M6 8.5h1M9 8.5h1M6 11h1M9 11h1" />
      <path d="M8 3v10.5" />
    </template>
    <template v-else-if="kind === 'chat'">
      <path d="M3 4.5h7a1.5 1.5 0 0 1 1.5 1.5v3.5a1.5 1.5 0 0 1-1.5 1.5H6l-2 2v-2.5" />
      <path d="M8.5 6.5h4a1.2 1.2 0 0 1 1.2 1.2v2.3a1.2 1.2 0 0 1-1.2 1.2H12l-1.5 1.5V11.2" />
    </template>
    <template v-else-if="kind === 'lens'">
      <circle cx="7" cy="7" r="2.6" />
      <circle cx="7" cy="7" r="1" />
      <path d="M9 9l2.5 2.5" />
    </template>
    <template v-else-if="kind === 'node' || kind === 'tower'">
      <path d="M8 2.5v2" />
      <path d="M6.5 4.5h3" />
      <path d="M8 4.5v7" />
      <path d="M5.5 11.5h5" />
      <path d="M4.5 6.5c0-1.2 1.6-2.2 3.5-2.2s3.5 1 3.5 2.2" />
    </template>
    <template v-else-if="kind === 'flask'">
      <path d="M6 3.5h4" />
      <path d="M7 3.5v2.5l-2 5.5h6l-2-5.5V3.5" />
      <path d="M6.5 9.5h3" />
    </template>
    <template v-else-if="kind === 'orbit'">
      <circle cx="8" cy="8" r="4.5" />
      <circle cx="8" cy="8" r="1.2" />
      <circle cx="11.5" cy="6" r="0.8" fill="currentColor" stroke="none" />
    </template>
    <template v-else>
      <path d="M8 2.5 12 5v5l-4 2.5-4-2.5V5z" />
      <path d="M8 2.5v5M4 5l4 2.5L12 5" />
    </template>
  </svg>
</template>
