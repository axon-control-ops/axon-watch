<script setup lang="ts">
import { computed, ref } from 'vue';

import { canHandoffSignalToIde } from '../../lib/signal-handoff-view';
import { useShellStore } from '../../stores/shell';

const props = defineProps<{
  signalId: string;
  workspaceId?: string | null;
  title: string;
  summary?: string | null;
  meta?: Record<string, unknown> | null;
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
    meta: props.meta,
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
        meta: props.meta,
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
    {{ pending || shell.handoffMutationState === 'submitting' ? 'Handing off…' : 'Investigate in IDE' }}
  </button>
</template>
