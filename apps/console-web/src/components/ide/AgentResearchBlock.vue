<script setup lang="ts">
import type { ResearchTranscriptItem } from '../../lib/agent-transcript-blocks';

defineProps<{
  query: string;
  items: ResearchTranscriptItem[];
  live?: boolean;
}>();
</script>

<template>
  <div class="agent-block agent-block--research">
    <div class="agent-block__research-header">
      <span class="agent-block__research-icon" aria-hidden="true">⌕</span>
      <span class="agent-block__research-query">{{ query }}</span>
      <span v-if="live" class="agent-block__research-live">searching…</span>
    </div>
    <ul v-if="items.length" class="agent-block__research-list">
      <li
        v-for="(item, index) in items"
        :key="`${item.url}:${index}`"
        class="agent-block__research-card hud-panel-frame"
      >
        <a
          v-if="item.url"
          class="agent-block__research-title"
          :href="item.url"
          target="_blank"
          rel="noopener noreferrer"
        >
          {{ item.title }}
        </a>
        <p v-else class="agent-block__research-title agent-block__research-title--plain">
          {{ item.title }}
        </p>
        <p v-if="item.url" class="agent-block__research-url">{{ item.url }}</p>
        <p v-if="item.snippet" class="agent-block__research-snippet">{{ item.snippet }}</p>
      </li>
    </ul>
    <p v-else-if="live" class="agent-block__research-empty">Gathering sources…</p>
  </div>
</template>
