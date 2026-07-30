import { onBeforeUnmount, watch, type Ref } from 'vue';

import { resolveWorkbenchTerminalAutoClose } from '../lib/workbench-terminal-auto-close';

/**
 * Previously auto-hid the workbench terminal after idle.
 * That path is disabled — keep the hook so call sites stay stable, but never hide.
 */
export function useWorkbenchTerminalAutoClose(input: {
  terminalPanelVisible: Ref<boolean>;
  onHideTerminal: () => void;
  /** Unused — retained for call-site compatibility. */
  dockSelector?: string;
}): void {
  const { terminalPanelVisible, onHideTerminal } = input;
  void onHideTerminal;
  void input.dockSelector;

  watch(
    terminalPanelVisible,
    (visible) => {
      // Explicit no-op: resolveWorkbenchTerminalAutoClose never arms.
      void resolveWorkbenchTerminalAutoClose({ terminalVisible: visible });
    },
    { immediate: true },
  );

  onBeforeUnmount(() => {
    /* nothing to clear — timers are not armed */
  });
}
