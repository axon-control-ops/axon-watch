<script setup lang="ts">
import type { IdeActivityView } from '../../lib/ide-layout-prefs';
import { useShellStore } from '../../stores/shell';

const shell = useShellStore();

const items: Array<{ id: IdeActivityView; label: string; glyph: string }> = [
  { id: 'explorer', label: 'Explorer', glyph: '▤' },
  { id: 'search', label: 'Search', glyph: '⌕' },
  { id: 'git', label: 'Source Control', glyph: '⑂' },
  { id: 'terminal', label: 'Terminal', glyph: '▭' },
  { id: 'agent', label: 'Agent Dock', glyph: '◎' },
];

function selectView(view: IdeActivityView): void {
  shell.setIdeActivityView(view);
}
</script>

<template>
  <nav class="ide-activity-bar" aria-label="IDE activity bar">
    <button
      v-for="item in items"
      :key="item.id"
      type="button"
      class="ide-activity-bar__button"
      :class="{ 'ide-activity-bar__button--active': shell.ideActivityView === item.id }"
      :aria-label="item.label"
      :title="item.label"
      @click="selectView(item.id)"
    >
      <span aria-hidden="true">{{ item.glyph }}</span>
    </button>
  </nav>
</template>
