import { computed, type ComputedRef, type Ref } from 'vue';

type TerminalPanelVisibility = Ref<boolean> | ComputedRef<boolean>;

import {
  workbenchTerminalPanelAlive,
  workbenchTerminalReopenAriaLabel,
  workbenchTerminalReopenTitle,
} from '../lib/workbench-terminal-panel-view';

export function useWorkbenchTerminalReopen(input: {
  terminalPanelVisible: TerminalPanelVisibility;
  runPhase: ComputedRef<string | null | undefined>;
}) {
  const terminalReopenAlive = computed(
    () =>
      !input.terminalPanelVisible.value &&
      workbenchTerminalPanelAlive(input.runPhase.value ?? null),
  );

  const terminalReopenTitle = computed(() =>
    workbenchTerminalReopenTitle({ runPhase: input.runPhase.value ?? null }),
  );

  const terminalReopenAriaLabel = computed(() =>
    workbenchTerminalReopenAriaLabel({ runPhase: input.runPhase.value ?? null }),
  );

  return {
    terminalReopenAlive,
    terminalReopenTitle,
    terminalReopenAriaLabel,
  };
}
