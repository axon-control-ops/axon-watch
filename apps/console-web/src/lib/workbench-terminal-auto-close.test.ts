import { describe, expect, it } from 'vitest';

import {
  resolveWorkbenchTerminalAutoClose,
  WORKBENCH_TERMINAL_AUTO_CLOSE_MS,
} from './workbench-terminal-auto-close';

describe('resolveWorkbenchTerminalAutoClose', () => {
  it('does not arm when the terminal is hidden', () => {
    expect(resolveWorkbenchTerminalAutoClose({ terminalVisible: false })).toEqual({
      shouldArm: false,
      delayMs: WORKBENCH_TERMINAL_AUTO_CLOSE_MS,
    });
  });

  it('does not arm when the terminal is visible (operator keeps the dock open)', () => {
    expect(resolveWorkbenchTerminalAutoClose({ terminalVisible: true })).toEqual({
      shouldArm: false,
      delayMs: WORKBENCH_TERMINAL_AUTO_CLOSE_MS,
    });
  });
});
