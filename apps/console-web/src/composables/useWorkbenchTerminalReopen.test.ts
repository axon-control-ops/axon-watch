import { computed, ref } from 'vue';
import { describe, expect, it } from 'vitest';

import { useWorkbenchTerminalReopen } from './useWorkbenchTerminalReopen';

describe('useWorkbenchTerminalReopen', () => {
  it('signals alive when the terminal is hidden during an active run phase', () => {
    const terminalPanelVisible = ref(false);
    const runPhase = computed(() => 'executing' as string | null);
    const { terminalReopenAlive, terminalReopenTitle, terminalReopenAriaLabel } =
      useWorkbenchTerminalReopen({ terminalPanelVisible, runPhase });

    expect(terminalReopenAlive.value).toBe(true);
    expect(terminalReopenTitle.value).toContain('Run in progress');
    expect(terminalReopenAriaLabel.value).toContain('run in progress');
  });

  it('stays quiet when the terminal panel is visible or no run needs attention', () => {
    const hidden = ref(false);
    const visible = ref(true);
    const idlePhase = computed(() => null as string | null);
    const executingPhase = computed(() => 'executing' as string | null);

    expect(
      useWorkbenchTerminalReopen({ terminalPanelVisible: visible, runPhase: executingPhase })
        .terminalReopenAlive.value,
    ).toBe(false);
    expect(
      useWorkbenchTerminalReopen({ terminalPanelVisible: hidden, runPhase: idlePhase })
        .terminalReopenAlive.value,
    ).toBe(false);
  });
});
