<script setup lang="ts">
withDefaults(
  defineProps<{
    name:
      | 'file'
      | 'close'
      | 'search'
      | 'split'
      | 'new-file'
      | 'book'
      | 'more'
      | 'plus'
      | 'trash'
      | 'folder'
      | 'folder-open'
      | 'new-folder'
      | 'history'
      | 'terminal'
      | 'terminal-agent';
    size?: number;
  }>(),
  { size: 14 },
);
</script>

<template>
  <svg
    class="workbench-icon"
    :width="size"
    :height="size"
    viewBox="0 0 16 16"
    fill="none"
    stroke="currentColor"
    stroke-width="1.1"
    stroke-linecap="round"
    stroke-linejoin="round"
    aria-hidden="true"
  >
    <template v-if="name === 'file'">
      <path d="M4.5 2.5h4.2l2.8 2.8v8.2H4.5z" />
      <path d="M8.7 2.5v2.8h2.8" />
    </template>
    <template v-else-if="name === 'close'">
      <path d="M4.5 4.5l7 7M11.5 4.5l-7 7" />
    </template>
    <template v-else-if="name === 'search'">
      <circle cx="7" cy="7" r="3.1" />
      <path d="M9.4 9.4L12 12" />
    </template>
    <template v-else-if="name === 'split'">
      <rect x="2.5" y="3" width="11" height="10" rx="0.5" />
      <path d="M8 3v10" />
    </template>
    <template v-else-if="name === 'new-file'">
      <path d="M4.5 2.5h4.2l2.8 2.8v8.2H4.5z" />
      <path d="M8 6.5v3M6.5 8h3" />
    </template>
    <template v-else-if="name === 'book'">
      <path d="M3.5 3.5h4.5a1.5 1.5 0 0 1 1.5 1.5V12" />
      <path d="M12.5 3.5H8a1.5 1.5 0 0 0-1.5 1.5V12" />
      <path d="M6.5 6h3M6.5 8.5h3" />
    </template>
    <template v-else-if="name === 'more'">
      <circle cx="4" cy="8" r="0.65" fill="currentColor" stroke="none" />
      <circle cx="8" cy="8" r="0.65" fill="currentColor" stroke="none" />
      <circle cx="12" cy="8" r="0.65" fill="currentColor" stroke="none" />
    </template>
    <template v-else-if="name === 'plus'">
      <path d="M8 3.5v9M3.5 8h9" />
    </template>
    <template v-else-if="name === 'trash'">
      <path d="M3.5 4.5h9" />
      <path d="M5.5 4.5V3.5h5v1" />
      <path d="M5 4.5l.5 7.5h5l.5-7.5" />
      <path d="M6.5 7v4M9.5 7v4" />
    </template>
    <template v-else-if="name === 'folder'">
      <path d="M2.5 4.5h4.2l1.4 1.5H13.5a1 1 0 0 1 1 1v5.5a1 1 0 0 1-1 1H3.5a1 1 0 0 1-1-1z" />
    </template>
    <template v-else-if="name === 'folder-open'">
      <path d="M2.5 4.5h4.2l1.4 1.5H13.5a1 1 0 0 1 1 1v1.5H3.2a1 1 0 0 0-.98 1.2l.8 3.8a1 1 0 0 0 .98.8h9.5a1 1 0 0 0 1-1V6.5a1 1 0 0 0-1-1H8.1z" />
    </template>
    <template v-else-if="name === 'new-folder'">
      <path d="M2.5 4.5h4.2l1.4 1.5H13.5a1 1 0 0 1 1 1v5.5a1 1 0 0 1-1 1H3.5a1 1 0 0 1-1-1z" />
      <path d="M8 6.3v3M6.5 7.8h3" />
    </template>
    <template v-else-if="name === 'history'">
      <circle cx="8" cy="8" r="4.5" />
      <path d="M8 5.2V8l2 1.4" />
      <path d="M5.2 3.2 4 2" />
    </template>
    <template v-else-if="name === 'terminal'">
      <rect x="2.5" y="3.5" width="11" height="9" rx="0.8" />
      <path d="M4.8 6.2l2 1.8-2 1.8M8.2 9.8h3" />
    </template>
    <template v-else-if="name === 'terminal-agent'">
      <rect x="2.5" y="3.5" width="11" height="9" rx="0.8" />
      <path d="M4.8 6.2l2 1.8-2 1.8M8.2 9.8h2.2" />
      <circle cx="12.25" cy="9.8" r="1" fill="currentColor" stroke="none" />
    </template>
  </svg>
</template>
