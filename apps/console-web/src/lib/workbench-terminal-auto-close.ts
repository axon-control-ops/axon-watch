/** Pure helpers for workbench terminal auto-close behavior. */

export const WORKBENCH_TERMINAL_AUTO_CLOSE_MS = 9_000;
export const WORKBENCH_TERMINAL_AUTO_CLOSE_IDLE_RESET_MS = 9_000;

export type WorkbenchTerminalAutoCloseDecision = {
  shouldArm: boolean;
  delayMs: number;
};

/** Arm auto-close whenever the terminal becomes visible. */
export function resolveWorkbenchTerminalAutoClose(input: {
  terminalVisible: boolean;
}): WorkbenchTerminalAutoCloseDecision {
  if (!input.terminalVisible) {
    return { shouldArm: false, delayMs: WORKBENCH_TERMINAL_AUTO_CLOSE_MS };
  }
  return { shouldArm: true, delayMs: WORKBENCH_TERMINAL_AUTO_CLOSE_MS };
}
