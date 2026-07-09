<script setup lang="ts">
import { computed, ref, watch } from 'vue';

import OperatorPersonaMark from '../../components/OperatorPersonaMark.vue';
import {
  buildIdeAgentThreadStatusLabel,
  parseIdeAgentThreadStatusLabel,
  shouldShowIdeAgentThreadStatusStrip,
} from '../../lib/ide-agent-center-view';
import { useShellStore } from '../../stores/shell';

const shell = useShellStore();
const expanded = ref(false);

const showStatusStrip = computed(() =>
  shouldShowIdeAgentThreadStatusStrip({
    layoutMode: shell.layoutMode,
    agentStreamActive: shell.agentStreamActive,
    activityLabel: shell.ideComposerActivity?.label,
  }),
);

const statusLabel = computed(() =>
  buildIdeAgentThreadStatusLabel({
    activityLabel: shell.ideComposerActivity?.label,
  }),
);

const statusBody = computed(() => parseIdeAgentThreadStatusLabel(statusLabel.value).body);
const canExpand = computed(() => Boolean(shell.ideComposerActivity?.liveBodyTruncated));
const visibleBody = computed(() =>
  expanded.value && shell.ideComposerActivity?.liveBodyFull
    ? shell.ideComposerActivity.liveBodyFull
    : statusBody.value,
);

watch(
  () => shell.ideComposerActivity?.label,
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
  <li
    v-if="showStatusStrip"
    class="conversation-seam__item conversation-seam__item--thread-status"
    role="status"
    aria-live="polite"
  >
    <p
      class="conversation-seam__thread-status-label"
      :class="{ 'conversation-seam__thread-status-label--expanded': expanded }"
    >
      <span class="persona-title">
        <OperatorPersonaMark size="xs" />
        <span class="conversation-seam__thread-status-body">— {{ visibleBody }}</span>
      </span>
      <button
        v-if="canExpand"
        type="button"
        class="conversation-seam__thread-status-expand"
        :aria-expanded="expanded"
        @click="toggleExpanded"
      >
        {{ expanded ? 'Show less' : 'Show more' }}
      </button>
    </p>
  </li>
</template>

<style scoped>
.conversation-seam__thread-status-label {
  display: flex;
  align-items: flex-start;
  gap: 0.45rem;
}

.conversation-seam__thread-status-label--expanded {
  align-items: flex-start;
}

.conversation-seam__thread-status-label--expanded .conversation-seam__thread-status-body {
  white-space: pre-wrap;
  overflow: visible;
  text-overflow: unset;
}

.conversation-seam__thread-status-expand {
  flex-shrink: 0;
  margin: 0;
  padding: 0;
  border: none;
  background: transparent;
  color: rgba(129, 140, 248, 0.92);
  cursor: pointer;
  font: inherit;
  font-size: 0.62rem;
  line-height: 1.35;
  text-decoration: underline;
  text-underline-offset: 0.12em;
}
</style>
