<script setup lang="ts">
import { nextTick, ref, watch } from 'vue';

import type { ComposerTypeaheadRow } from '../../../composables/agent-dock/use-composer-typeahead';
import {
  COMPOSER_TYPEAHEAD_LISTBOX_ID,
  composerTypeaheadOptionId,
} from '../../../lib/composer-typeahead-view';

const props = defineProps<{
  open: boolean;
  caption: string;
  emptyHint?: string;
  loading: boolean;
  rows: ComposerTypeaheadRow[];
  selectedIndex: number;
}>();

const emit = defineEmits<{
  select: [row: ComposerTypeaheadRow];
  hover: [index: number];
}>();

const panelRef = ref<HTMLElement | null>(null);

function scrollSelectedOptionIntoView(): void {
  const panel = panelRef.value;
  if (!panel || !props.open || !props.rows.length) {
    return;
  }
  const option = panel.querySelector<HTMLElement>(
    `#${CSS.escape(composerTypeaheadOptionId(props.selectedIndex))}`,
  );
  option?.scrollIntoView({ block: 'nearest', inline: 'nearest' });
}

watch(
  () => [props.open, props.selectedIndex, props.rows.length] as const,
  async () => {
    await nextTick();
    scrollSelectedOptionIntoView();
  },
);

function rowCommand(row: ComposerTypeaheadRow): string {
  return row.kind === 'file' ? `@file:${row.path}` : row.command;
}

function rowLabel(row: ComposerTypeaheadRow): string {
  return row.label;
}

function rowDetail(row: ComposerTypeaheadRow): string {
  return row.kind === 'file' ? 'Workspace file' : row.detail;
}

function rowKindLabel(row: ComposerTypeaheadRow): string {
  if (row.kind === 'file') {
    return 'file';
  }
  if (row.kind === 'mode') {
    return 'mode';
  }
  if (row.kind === 'command') {
    return 'cmd';
  }
  return 'skill';
}
</script>

<template>
  <div
    v-if="open"
    :id="COMPOSER_TYPEAHEAD_LISTBOX_ID"
    ref="panelRef"
    class="agent-dock-composer__typeahead"
    role="listbox"
    :aria-label="caption"
  >
    <header class="agent-dock-composer__typeahead-head">
      <p class="agent-dock-composer__menu-caption">
        {{ caption }}
      </p>
      <p class="agent-dock-composer__typeahead-hint">
        ↑↓ navigate · Tab complete · Enter apply · Esc close
      </p>
    </header>
    <p
      v-if="loading && !rows.length"
      class="agent-dock-composer__menu-note"
    >
      Loading…
    </p>
    <p
      v-else-if="!rows.length"
      class="agent-dock-composer__menu-note"
    >
      {{ emptyHint || 'No matches' }}
    </p>
    <button
      v-for="(row, index) in rows"
      :id="composerTypeaheadOptionId(index)"
      :key="'id' in row ? row.id : rowCommand(row)"
      type="button"
      class="agent-dock-composer__menu-item agent-dock-composer__typeahead-item"
      :class="{ 'is-active': index === selectedIndex }"
      role="option"
      :aria-selected="index === selectedIndex"
      @mousedown.prevent="emit('select', row)"
      @mouseenter="emit('hover', index)"
    >
      <span class="agent-dock-composer__typeahead-row">
        <span
          class="agent-dock-composer__typeahead-kind"
          :data-kind="row.kind === 'file' ? 'file' : row.kind"
        >
          {{ rowKindLabel(row) }}
        </span>
        <strong>{{ rowCommand(row) }}</strong>
        <span class="agent-dock-composer__typeahead-label">{{ rowLabel(row) }}</span>
      </span>
      <small>{{ rowDetail(row) }}</small>
    </button>
  </div>
</template>
