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
  return 'command' in row ? row.command : `@file:${row.path}`;
}

function rowLabel(row: ComposerTypeaheadRow): string {
  return 'label' in row ? row.label : row.path;
}

function rowDetail(row: ComposerTypeaheadRow): string {
  if ('detail' in row) {
    return row.detail;
  }
  return 'Workspace file';
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
    <p class="agent-dock-composer__menu-caption">
      {{ caption }}
    </p>
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
      No matches
    </p>
    <button
      v-for="(row, index) in rows"
      :id="composerTypeaheadOptionId(index)"
      :key="'id' in row ? row.id : rowCommand(row)"
      type="button"
      class="agent-dock-composer__menu-item"
      :class="{ 'is-active': index === selectedIndex }"
      role="option"
      :aria-selected="index === selectedIndex"
      @mousedown.prevent="emit('select', row)"
      @mouseenter="emit('hover', index)"
    >
      <strong>{{ rowCommand(row) }}</strong>
      <small>{{ rowLabel(row) }} — {{ rowDetail(row) }}</small>
    </button>
  </div>
</template>
