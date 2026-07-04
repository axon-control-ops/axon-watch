<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from 'vue';

import { createXtermSession } from '../lib/create-xterm-session';

const props = defineProps<{
  primarySignalId: string | null;
  runtimeConnected: boolean;
  runSummary: string | null;
  workspaceId: string | null;
  variant?: 'default' | 'mockup';
}>();

const containerRef = ref<HTMLElement | null>(null);
const loadState = ref<'loading' | 'ready' | 'error'>('loading');
let terminalController: Awaited<ReturnType<typeof createXtermSession>> | null = null;

function clearTerminal(): void {
  terminalController?.clearScreen();
}

function persistTerminalScrollback(): void {
  terminalController?.persistScrollback();
}

defineExpose({
  clearTerminal,
  persistTerminalScrollback,
});

function handleBeforeUnload(): void {
  persistTerminalScrollback();
}

onMounted(async () => {
  if (!containerRef.value) {
    loadState.value = 'error';
    return;
  }

  window.addEventListener('beforeunload', handleBeforeUnload);

  try {
    terminalController = await createXtermSession(containerRef.value, {
      variant: props.variant,
    });
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
  window.removeEventListener('beforeunload', handleBeforeUnload);
  persistTerminalScrollback();
  terminalController?.dispose();
  terminalController = null;
});
</script>

<template>
  <div
    class="surface-host surface-host--terminal"
    :class="{ 'surface-host--terminal-mockup': variant === 'mockup' }"
  >
    <p v-if="loadState === 'loading'" class="surface-host__status">Loading terminal…</p>
    <p v-else-if="loadState === 'error'" class="surface-host__status">Terminal host unavailable</p>
    <div class="surface-host__body">
      <div ref="containerRef" class="surface-host__frame" aria-label="xterm terminal host" />
    </div>
  </div>
</template>
