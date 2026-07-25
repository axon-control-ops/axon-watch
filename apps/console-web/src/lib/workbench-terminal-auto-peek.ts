export type WorkbenchTerminalAutoPeekInput = {
  layoutMode: 'operator' | 'ide';
  terminalVisible: boolean;
  runPhase: string | null;
  runId: string | null;
  alreadyPeekedRunIds: ReadonlySet<string>;
};

/** Terminal never auto-opens — operator must reveal it (status chip / Ctrl+J / agent tool). */
export function shouldAutoPeekWorkbenchTerminal(
  _input: WorkbenchTerminalAutoPeekInput,
): boolean {
  return false;
}
