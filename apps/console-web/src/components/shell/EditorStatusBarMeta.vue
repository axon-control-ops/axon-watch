<script setup lang="ts">
import type { EditorAccessStatus } from '../../lib/editor-access-status-view';

defineProps<{
  showMinimapToggle: boolean;
  minimapEnabled: boolean;
  cursorLine: number;
  cursorColumn: number;
  lineCount: number;
  eol: 'CRLF' | 'LF';
  languageLabel: string;
  accessStatus: EditorAccessStatus;
}>();

const emit = defineEmits<{
  toggleMinimap: [];
  openSourceControl: [];
}>();
</script>

<template>
  <div class="editor-statusbar__meta">
    <button
      v-if="showMinimapToggle"
      type="button"
      class="editor-statusbar__toggle"
      :class="{ 'editor-statusbar__toggle--active': minimapEnabled }"
      title="Toggle minimap"
      aria-label="Toggle minimap"
      @click="emit('toggleMinimap')"
    >
      Minimap
    </button>
    <span>Ln {{ cursorLine }}, Col {{ cursorColumn }}</span>
    <span>{{ lineCount }} line{{ lineCount === 1 ? '' : 's' }}</span>
    <span>Spaces: 2</span>
    <span>UTF-8</span>
    <span>{{ eol }}</span>
    <span>{{ languageLabel }}</span>
    <button
      v-if="accessStatus.opensSourceControl"
      type="button"
      class="editor-statusbar__state editor-statusbar__state--unsaved"
      :title="accessStatus.title"
      :aria-label="accessStatus.ariaLabel"
      @click="emit('openSourceControl')"
    >
      {{ accessStatus.label }}
    </button>
    <span
      v-else
      class="editor-statusbar__state"
      :class="`editor-statusbar__state--${accessStatus.tone}`"
      :title="accessStatus.title"
      :aria-label="accessStatus.ariaLabel ?? accessStatus.label"
    >
      {{ accessStatus.label }}
    </span>
  </div>
</template>
