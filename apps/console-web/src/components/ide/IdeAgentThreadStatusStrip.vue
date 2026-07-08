<script setup lang="ts">
import { computed } from 'vue';

import OperatorPersonaMark from '../../components/OperatorPersonaMark.vue';
import {
  buildIdeAgentThreadStatusLabel,
  parseIdeAgentThreadStatusLabel,
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

const statusBody = computed(() => parseIdeAgentThreadStatusLabel(statusLabel.value).body);
</script>

<template>
  <li
    v-if="showStatusStrip"
    class="conversation-seam__item conversation-seam__item--thread-status"
    role="status"
    aria-live="polite"
  >
    <p class="conversation-seam__thread-status-label">
      <span class="persona-title">
        <OperatorPersonaMark size="xs" />
        <span class="conversation-seam__thread-status-body">— {{ statusBody }}</span>
      </span>
    </p>
  </li>
</template>
