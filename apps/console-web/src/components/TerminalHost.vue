<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from 'vue';

import { createXtermSession } from '../lib/create-xterm-session';

const props = defineProps<{
  primarySignalId: string | null;
  readOnly?: boolean;
  runtimeConnected: boolean;
  runSummary: string | null;
  workspaceId: string | null;
  sessionId?: string;
  sessionRole?: string;
  variant?: 'default' | 'mockup';
}>();

const containerRef = ref<HTMLElement | null>(null);
const loadState = ref<'loading' | 'ready' | 'error'>('loading');
let terminalController: Awaited<ReturnType<typeof createXtermSession>> | null = null;
let unmounted = false;

function clearTerminal(): void {
  terminalController?.clearScreen();
}

function persistTerminalScrollback(): void {
  terminalController?.persistScrollback();
}

function writeMirrorSnapshot(text: string): void {
  terminalController?.writeMirrorSnapshot(text);
}

function exitMirrorMode(): void {
  terminalController?.exitMirrorMode();
}

function writeInput(data: string): void {
  terminalController?.writeInput(data);
}

function runCommand(command: string): void {
  terminalController?.runCommand(command);
}

defineExpose({
  clearTerminal,
  persistTerminalScrollback,
  writeMirrorSnapshot,
  exitMirrorMode,
  writeInput,
  runCommand,
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
    const session = await createXtermSession(containerRef.value, {
      readOnly: props.readOnly ?? props.sessionRole === 'agent',
      variant: props.variant,
    });
    if (unmounted) {
      // Component was torn down while the session was still connecting —
      // onBeforeUnmount already ran and found terminalController null, so
      // dispose this one ourselves instead of leaking the socket/xterm instance.
      session.dispose();
      return;
    }
    terminalController = session;
    terminalController.setContext({
      workspaceId: props.workspaceId,
      runSummary: props.runSummary,
      primarySignalId: props.primarySignalId,
      runtimeConnected: props.runtimeConnected,
      sessionId: props.sessionId ?? 'terminal-operator',
      sessionRole: props.sessionRole ?? 'operator',
    });
    loadState.value = 'ready';
  } catch {
    if (!unmounted) {
      loadState.value = 'error';
    }
  }
});

watch(
  () => ({
    workspaceId: props.workspaceId,
    runSummary: props.runSummary,
    primarySignalId: props.primarySignalId,
    runtimeConnected: props.runtimeConnected,
    sessionId: props.sessionId ?? 'terminal-operator',
    sessionRole: props.sessionRole ?? 'operator',
  }),
  (context) => {
    terminalController?.setContext(context);
  },
  { deep: true },
);

onBeforeUnmount(() => {
  unmounted = true;
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
