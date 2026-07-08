<script setup lang="ts">
import { computed } from 'vue';

import {
  buildIdeAgentThreadStatusLabel,
  shouldShowIdeAgentThreadStatusStrip,
} from '../../lib/ide-agent-center-view';
import { useShellStore } from '../../stores/shell';

const shell = useShellStore();

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
</script>

<template>
  <li
    v-if="showStatusStrip"
    class="conversation-seam__item conversation-seam__item--thread-status"
    role="status"
    aria-live="polite"
  >
    <p class="conversation-seam__thread-status-label">{{ statusLabel }}</p>
  </li>
</template>
