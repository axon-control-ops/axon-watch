export type WorkbenchTerminalAutoPeekInput = {
  layoutMode: 'operator' | 'ide';
  terminalVisible: boolean;
  runPhase: string | null;
  runId: string | null;
  alreadyPeekedRunIds: ReadonlySet<string>;
};

const AUTO_PEEK_RUN_PHASES = new Set(['executing', 'review_ready']);

/** Open the workbench terminal once per run when shell output matters. */
export function shouldAutoPeekWorkbenchTerminal(
  input: WorkbenchTerminalAutoPeekInput,
): boolean {
  if (input.terminalVisible) {
    return false;
  }

  if (input.layoutMode !== 'operator' && input.layoutMode !== 'ide') {
    return false;
  }

  const runId = input.runId?.trim() ?? '';
  const phase = input.runPhase ?? '';
  if (!runId || !AUTO_PEEK_RUN_PHASES.has(phase)) {
    return false;
  }

  return !input.alreadyPeekedRunIds.has(runId);
}
