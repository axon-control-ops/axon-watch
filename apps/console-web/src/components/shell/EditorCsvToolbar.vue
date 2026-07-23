<script setup lang="ts">
defineProps<{
  tableEnabled: boolean;
}>();

const emit = defineEmits<{
  setTable: [enabled: boolean];
}>();
</script>

<template>
  <div class="editor-markdown-toolbar editor-view-mode-toolbar">
    <div
      class="conversation-seam__markdown-mode-toggle editor-markdown-toolbar__toggle"
      role="group"
      aria-label="Editor table view mode"
    >
      <button
        type="button"
        class="conversation-seam__markdown-mode-button"
        :class="{ 'conversation-seam__markdown-mode-button--active': tableEnabled }"
        :aria-pressed="tableEnabled"
        @click="emit('setTable', true)"
      >
        Table
      </button>
      <button
        type="button"
        class="conversation-seam__markdown-mode-button"
        :class="{ 'conversation-seam__markdown-mode-button--active': !tableEnabled }"
        :aria-pressed="!tableEnabled"
        @click="emit('setTable', false)"
      >
        Raw
      </button>
    </div>
  </div>
</template>
