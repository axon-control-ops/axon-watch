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
      | 'clear'
      | 'chevron-down'
      | 'folder'
      | 'folder-open'
      | 'new-folder'
      | 'history'
      | 'terminal'
      | 'terminal-agent'
      | 'shell-zsh'
      | 'shell-bash';
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
    stroke-width="1.35"
    stroke-linecap="round"
    stroke-linejoin="round"
    aria-hidden="true"
  >
    <template v-if="name === 'file'">
      <path d="M4.25 2.25h4.4L12 5.6v8.15H4.25z" />
      <path d="M8.65 2.25v3.35H12" />
    </template>
    <template v-else-if="name === 'close'">
      <path d="M4.2 4.2l7.6 7.6M11.8 4.2l-7.6 7.6" />
    </template>
    <template v-else-if="name === 'search'">
      <circle cx="7" cy="7" r="3.25" />
      <path d="M9.55 9.55L12.4 12.4" />
    </template>
    <template v-else-if="name === 'split'">
      <rect x="2.25" y="2.75" width="11.5" height="10.5" rx="1.1" />
      <path d="M8 2.75v10.5" />
    </template>
    <template v-else-if="name === 'new-file'">
      <path d="M4.25 2.25h4.4L12 5.6v8.15H4.25z" />
      <path d="M8.65 2.25v3.35H12" />
      <path d="M8 7.1v3.4M6.3 8.8h3.4" />
    </template>
    <template v-else-if="name === 'book'">
      <path d="M3.25 3.25h4.6a1.6 1.6 0 0 1 1.6 1.6V12.5" />
      <path d="M12.75 3.25H8.15a1.6 1.6 0 0 0-1.6 1.6V12.5" />
      <path d="M6.4 6.2h3.2M6.4 8.7h3.2" />
    </template>
    <template v-else-if="name === 'more'">
      <circle cx="4" cy="8" r="0.85" fill="currentColor" stroke="none" />
      <circle cx="8" cy="8" r="0.85" fill="currentColor" stroke="none" />
      <circle cx="12" cy="8" r="0.85" fill="currentColor" stroke="none" />
    </template>
    <template v-else-if="name === 'plus'">
      <path d="M8 3.1v9.8M3.1 8h9.8" />
    </template>
    <template v-else-if="name === 'trash'">
      <path d="M3.2 4.4h9.6" />
      <path d="M5.5 4.4V3.35h5V4.4" />
      <path d="M4.85 4.4l.55 8.1h5.2l.55-8.1" />
      <path d="M6.55 6.7v4.2M9.45 6.7v4.2" />
    </template>
    <template v-else-if="name === 'clear'">
      <!-- Eraser / clear scrollback -->
      <path d="M3.1 10.2 9.4 3.9a1.2 1.2 0 0 1 1.7 0l1.05 1.05a1.2 1.2 0 0 1 0 1.7L6.15 12.9" />
      <path d="M7.6 5.7l2.75 2.75" />
      <path d="M2.75 12.9h6.4" />
    </template>
    <template v-else-if="name === 'chevron-down'">
      <path d="M3.6 6.2 8 10.4l4.4-4.2" />
    </template>
    <template v-else-if="name === 'folder'">
      <path d="M2.25 4.4h4.3l1.35 1.45H13.7a.9.9 0 0 1 .9.9v5.4a.9.9 0 0 1-.9.9H3.2a.9.9 0 0 1-.9-.9z" />
    </template>
    <template v-else-if="name === 'folder-open'">
      <path d="M2.25 4.4h4.3l1.35 1.45H13.7a.9.9 0 0 1 .9.9v1.35H3.15a.95.95 0 0 0-.93 1.15l.75 3.55a.9.9 0 0 0 .88.7h9.35a.9.9 0 0 0 .9-.9V6.75a.9.9 0 0 0-.9-.9H8.05z" />
    </template>
    <template v-else-if="name === 'new-folder'">
      <path d="M2.25 4.4h4.3l1.35 1.45H13.7a.9.9 0 0 1 .9.9v5.4a.9.9 0 0 1-.9.9H3.2a.9.9 0 0 1-.9-.9z" />
      <path d="M8 6.55v3.3M6.35 8.2h3.3" />
    </template>
    <template v-else-if="name === 'history'">
      <circle cx="8" cy="8.2" r="4.6" />
      <path d="M8 5.35V8.2l2.15 1.45" />
      <path d="M5.05 3.15 3.9 2.05" />
    </template>
    <template v-else-if="name === 'terminal'">
      <rect x="2.2" y="3.2" width="11.6" height="9.6" rx="1.2" />
      <path d="M4.55 6.1l2.2 1.9-2.2 1.9M8.1 9.9h3.2" />
    </template>
    <template v-else-if="name === 'terminal-agent'">
      <rect x="2.2" y="3.2" width="11.6" height="9.6" rx="1.2" />
      <path d="M4.55 6.1l2.2 1.9-2.2 1.9M8.1 9.9h2.15" />
      <circle cx="12.15" cy="9.9" r="1.15" fill="currentColor" stroke="none" />
    </template>
    <template v-else-if="name === 'shell-zsh'">
      <rect x="2.2" y="3.2" width="11.6" height="9.6" rx="1.2" />
      <path d="M4.55 6.1l2.2 1.9-2.2 1.9M8.1 9.9h3.2" />
    </template>
    <template v-else-if="name === 'shell-bash'">
      <rect x="2.2" y="3.2" width="11.6" height="9.6" rx="1.2" />
      <path d="M5.1 6.35h2.4M5.1 8h3.6M5.1 9.65h2.9" />
    </template>
  </svg>
</template>
