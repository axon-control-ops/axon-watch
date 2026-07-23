import { onBeforeUnmount, watch, type Ref } from 'vue';

import {
  resolveWorkbenchTerminalAutoClose,
  WORKBENCH_TERMINAL_AUTO_CLOSE_IDLE_RESET_MS,
} from '../lib/workbench-terminal-auto-close';

/** Auto-hide the workbench terminal after idle; interaction resets the timer. */
export function useWorkbenchTerminalAutoClose(input: {
  terminalPanelVisible: Ref<boolean>;
  onHideTerminal: () => void;
  /** Selector for the dock root used to reset idle on operator interaction. */
  dockSelector?: string;
}): void {
  const { terminalPanelVisible, onHideTerminal, dockSelector = '.center-workbench__terminal-panel' } =
    input;

  let closeTimer: number | null = null;

  function clearCloseTimer(): void {
    if (closeTimer !== null) {
      window.clearTimeout(closeTimer);
      closeTimer = null;
    }
  }

  function armCloseTimer(): void {
    clearCloseTimer();
    const decision = resolveWorkbenchTerminalAutoClose({
      terminalVisible: terminalPanelVisible.value,
    });
    if (!decision.shouldArm) {
      return;
    }
    closeTimer = window.setTimeout(() => {
      closeTimer = null;
      if (terminalPanelVisible.value) {
        onHideTerminal();
      }
    }, decision.delayMs);
  }

  function onDockActivity(event: Event): void {
    const target = event.target;
    if (!(target instanceof Element)) {
      return;
    }
    if (!target.closest(dockSelector)) {
      return;
    }
    if (!terminalPanelVisible.value) {
      return;
    }
    clearCloseTimer();
    closeTimer = window.setTimeout(() => {
      closeTimer = null;
      if (terminalPanelVisible.value) {
        onHideTerminal();
      }
    }, WORKBENCH_TERMINAL_AUTO_CLOSE_IDLE_RESET_MS);
  }

  watch(
    terminalPanelVisible,
    (visible) => {
      if (!visible) {
        clearCloseTimer();
        return;
      }
      armCloseTimer();
    },
    { immediate: true },
  );

  if (typeof window !== 'undefined') {
    window.addEventListener('pointerdown', onDockActivity, true);
    window.addEventListener('keydown', onDockActivity, true);
  }

  onBeforeUnmount(() => {
    clearCloseTimer();
    if (typeof window !== 'undefined') {
      window.removeEventListener('pointerdown', onDockActivity, true);
      window.removeEventListener('keydown', onDockActivity, true);
    }
  });
}
