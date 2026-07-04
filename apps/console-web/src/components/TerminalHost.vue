<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from 'vue';

import { createXtermSession } from '../lib/create-xterm-session';

const props = defineProps<{
  primarySignalId: string | null;
  runtimeConnected: boolean;
  runSummary: string | null;
  workspaceId: string | null;
}>();

const containerRef = ref<HTMLElement | null>(null);
const loadState = ref<'loading' | 'ready' | 'error'>('loading');
let terminalController: Awaited<ReturnType<typeof createXtermSession>> | null = null;

onMounted(async () => {
  if (!containerRef.value) {
    loadState.value = 'error';
    return;
  }

  try {
    terminalController = await createXtermSession(containerRef.value);
    terminalController.setContext({
      workspaceId: props.workspaceId,
      runSummary: props.runSummary,
      primarySignalId: props.primarySignalId,
      runtimeConnected: props.runtimeConnected,
    });
    loadState.value = 'ready';
  } catch {
    loadState.value = 'error';
  }
});

watch(
  () => ({
    workspaceId: props.workspaceId,
    runSummary: props.runSummary,
    primarySignalId: props.primarySignalId,
    runtimeConnected: props.runtimeConnected,
  }),
  (context) => {
    terminalController?.setContext(context);
  },
  { deep: true },
);

onBeforeUnmount(() => {
  terminalController?.dispose();
  terminalController = null;
});
</script>

<template>
  <div class="surface-host surface-host--terminal">
    <p v-if="loadState === 'loading'" class="surface-host__status">Loading terminal…</p>
    <p v-else-if="loadState === 'error'" class="surface-host__status">Terminal host unavailable</p>
    <div class="surface-host__body">
      <div ref="containerRef" class="surface-host__frame" aria-label="xterm terminal host" />
    </div>
  </div>
</template>
