<script setup lang="ts">
withDefaults(
  defineProps<{
    name: 'explorer' | 'search' | 'git' | 'run' | 'team' | 'terminal' | 'agent';
    size?: number;
  }>(),
  { size: 18 },
);
</script>

<template>
  <svg
    class="ide-activity-icon"
    :width="size"
    :height="size"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    stroke-width="1.8"
    stroke-linecap="round"
    stroke-linejoin="round"
    aria-hidden="true"
  >
    <template v-if="name === 'explorer'">
      <path d="M3.75 7.5A2.25 2.25 0 0 1 6 5.25h4.2l2.1 2.25H18A2.25 2.25 0 0 1 20.25 9.75v6.75A2.25 2.25 0 0 1 18 18.75H6A2.25 2.25 0 0 1 3.75 16.5z" />
    </template>
    <template v-else-if="name === 'search'">
      <circle cx="11" cy="11" r="6.25" />
      <path d="M20 20l-3.75-3.75" />
    </template>
    <template v-else-if="name === 'git'">
      <circle cx="7" cy="7" r="2.2" />
      <circle cx="17" cy="17" r="2.2" />
      <path d="M7 9v4a3 3 0 0 0 3 3h4" />
    </template>
    <template v-else-if="name === 'run'">
      <polygon points="8 5 19 12 8 19 8 5" />
    </template>
    <template v-else-if="name === 'team'">
      <circle cx="9" cy="8" r="2.4" />
      <circle cx="16" cy="9" r="2" />
      <path d="M4.5 18.2c0.4-3.1 2.5-4.7 4.5-4.7s4.1 1.6 4.5 4.7" />
      <path d="M13.2 18.2c0.25-1.9 1.2-3.2 2.8-3.2 1.7 0 2.85 1.35 3.05 3.2" />
    </template>
    <template v-else-if="name === 'terminal'">
      <polyline points="4 17 10 11 4 5" />
      <line x1="12" y1="19" x2="20" y2="19" />
    </template>
    <template v-else-if="name === 'agent'">
      <path d="M9 3.8a3.2 3.2 0 0 0-3.05 2.42A3.6 3.6 0 0 0 4 12.08a3.45 3.45 0 0 0 2.98 5.15H9V3.8Z" />
      <path d="M15 3.8a3.2 3.2 0 0 1 3.05 2.42A3.6 3.6 0 0 1 20 12.08a3.45 3.45 0 0 1-2.98 5.15H15V3.8Z" />
      <path d="M12 4.35v14.2" />
    </template>
  </svg>
</template>
