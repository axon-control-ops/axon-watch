<script setup lang="ts">
import { nextTick, ref, watch } from 'vue';

import type { SidebarTranscriptLine } from '../../lib/sidebar-agent-transcript-view';

const props = defineProps<{
  lines: SidebarTranscriptLine[];
  streaming: boolean;
  emptyHint: string;
  personaName: string;
}>();

const emit = defineEmits<{
  openDock: [];
}>();

const scrollerRef = ref<HTMLElement | null>(null);

watch(
  () => [props.lines.length, props.lines.at(-1)?.text, props.streaming] as const,
  async () => {
    await nextTick();
    const el = scrollerRef.value;
    if (!el) {
      return;
    }
    el.scrollTop = el.scrollHeight;
  },
);
</script>

<template>
  <section
    class="kairo-sidebar-transcript"
    :data-streaming="streaming ? 'true' : 'false'"
    :aria-label="`${personaName} agent transcript`"
    @click.stop
  >
    <header class="kairo-sidebar-transcript__header">
      <span class="kairo-sidebar-transcript__label">Agent transcript</span>
      <button
        type="button"
        class="kairo-sidebar-transcript__open-dock"
        @click="emit('openDock')"
      >
        Open dock
      </button>
    </header>

    <div ref="scrollerRef" class="kairo-sidebar-transcript__scroller">
      <p v-if="!lines.length" class="kairo-sidebar-transcript__empty">
        {{ emptyHint }}
      </p>
      <ul v-else class="kairo-sidebar-transcript__list">
        <li
          v-for="line in lines"
          :key="line.id"
          class="kairo-sidebar-transcript__line"
          :data-kind="line.kind"
          :data-live="line.live ? 'true' : 'false'"
        >
          <span class="kairo-sidebar-transcript__kind">{{ line.kind }}</span>
          <span class="kairo-sidebar-transcript__text">{{ line.text }}</span>
        </li>
      </ul>
    </div>
  </section>
</template>
