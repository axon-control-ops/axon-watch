<script setup lang="ts">
import { computed, ref, watch } from 'vue';

import type { IdeComposerActivity } from '../../lib/agent-dock-activity-view';

const props = defineProps<{
  activity: IdeComposerActivity | null;
  fallback: string;
}>();

const expanded = ref(false);

const headline = computed(() => {
  if (props.activity?.label) {
    return props.activity.label.replace(/^KAIRO —\s*/, '');
  }
  return props.fallback;
});

const canExpand = computed(() => Boolean(props.activity?.liveBodyTruncated));
const visibleText = computed(() =>
  expanded.value && props.activity?.liveBodyFull ? props.activity.liveBodyFull : headline.value,
);

watch(
  () => props.activity?.label,
  () => {
    expanded.value = false;
  },
);

function toggleExpanded(event: Event): void {
  event.preventDefault();
  event.stopPropagation();
  expanded.value = !expanded.value;
}
</script>

<template>
  <p
    class="agent-live-line-headline"
    :class="{ 'agent-live-line-headline--expanded': expanded }"
  >
    <span class="agent-live-line-headline__text">{{ visibleText }}</span>
    <button
      v-if="canExpand"
      type="button"
      class="agent-live-line-headline__expand"
      :aria-expanded="expanded"
      @click="toggleExpanded"
    >
      {{ expanded ? 'Less' : 'More' }}
    </button>
  </p>
</template>

<style scoped>
.agent-live-line-headline {
  margin: 0;
  display: flex;
  align-items: flex-start;
  gap: 0.35rem;
}

.agent-live-line-headline__text {
  min-width: 0;
}

.agent-live-line-headline--expanded .agent-live-line-headline__text {
  white-space: pre-wrap;
}

.agent-live-line-headline__expand {
  flex-shrink: 0;
  margin: 0;
  padding: 0;
  border: none;
  background: transparent;
  color: rgba(129, 140, 248, 0.92);
  cursor: pointer;
  font: inherit;
  font-size: 0.62rem;
  text-decoration: underline;
  text-underline-offset: 0.12em;
}
</style>
