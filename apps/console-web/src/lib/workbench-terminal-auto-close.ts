/** Pure helpers for workbench terminal auto-close behavior. */

export const WORKBENCH_TERMINAL_AUTO_CLOSE_MS = 9_000;
export const WORKBENCH_TERMINAL_AUTO_CLOSE_IDLE_RESET_MS = 9_000;

export type WorkbenchTerminalAutoCloseDecision = {
  shouldArm: boolean;
  delayMs: number;
};

/**
 * Keep the IDE terminal open once the operator opens it.
 * Auto-hide was hiding local shells after 9s idle and felt like a crash.
 */
export function resolveWorkbenchTerminalAutoClose(input: {
  terminalVisible: boolean;
}): WorkbenchTerminalAutoCloseDecision {
  void input.terminalVisible;
  return { shouldArm: false, delayMs: WORKBENCH_TERMINAL_AUTO_CLOSE_MS };
}
