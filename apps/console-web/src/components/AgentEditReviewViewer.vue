<script setup lang="ts">
import { computed } from 'vue';

import { diffLineTone } from '../lib/agent-transcript-blocks';

const props = defineProps<{
  content: string;
}>();

const lines = computed(() =>
  props.content.split('\n').map((text) => ({
    text,
    tone: diffLineTone(text),
  })),
);
</script>

<template>
  <pre class="agent-edit-review-viewer" aria-label="Agent edit review diff">
    <span
      v-for="(line, index) in lines"
      :key="index"
      class="agent-block__diff-line"
      :class="`agent-block__diff-line--${line.tone}`"
    >{{ line.text }}
</span>
  </pre>
</template>
