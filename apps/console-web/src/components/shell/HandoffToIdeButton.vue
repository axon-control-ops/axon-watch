<script setup lang="ts">
import { computed, ref } from 'vue';

import { canHandoffSignalToIde } from '../../lib/signal-handoff-view';
import { useShellStore } from '../../stores/shell';

const props = defineProps<{
  signalId: string;
  workspaceId?: string | null;
  title: string;
  summary?: string | null;
  compact?: boolean;
}>();

const shell = useShellStore();
const pending = ref(false);

const visible = computed(() =>
  canHandoffSignalToIde({
    signal_id: props.signalId,
    workspace_id: props.workspaceId,
    title: props.title,
    summary: props.summary,
  }),
);

async function handleHandoff(): Promise<void> {
  if (pending.value) {
    return;
  }
  pending.value = true;
  try {
    await shell.handoffSignalToIde(
      {
        signal_id: props.signalId,
        workspace_id: props.workspaceId,
        title: props.title,
        summary: props.summary,
      },
      { autoSubmit: true },
    );
  } finally {
    pending.value = false;
  }
}
</script>

<template>
  <button
    v-if="visible"
    type="button"
    class="handoff-to-ide-button"
    :class="{ 'handoff-to-ide-button--compact': compact }"
    :disabled="pending || shell.handoffMutationState === 'submitting'"
    @click.stop="handleHandoff"
  >
    {{ pending || shell.handoffMutationState === 'submitting' ? 'Handing off…' : 'Continue in IDE' }}
  </button>
</template>
