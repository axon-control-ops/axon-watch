export type OperatorQuickGuide = {
  title: string;
  steps: string[];
};

function terminalReopenSteps(): string[] {
  return [
    'Open terminal (Ctrl/Cmd+J) to follow live command output in the workbench.',
    'Header chip Open terminal, or the bottom Terminal dock strip → Show.',
  ];
}

export function buildOperatorQuickGuide(input: {
  runPhase: string | null;
  hasActiveRun: boolean;
  pendingApprovals: number;
  layoutMode: 'operator' | 'ide';
  terminalVisible?: boolean;
}): OperatorQuickGuide | null {
  if (input.layoutMode !== 'operator') {
    return null;
  }

  const terminalVisible = input.terminalVisible ?? true;
  const withTerminalHint = (steps: string[]): string[] =>
    terminalVisible ? steps : [...terminalReopenSteps(), ...steps];

  if (input.pendingApprovals > 0) {
    return {
      title: 'Approval waiting — decide before more work runs',
      steps: withTerminalHint([
        'Center Mission Control → APPROVE RUN or REJECT RUN.',
        'Left sidebar → Attention to read why approval was requested.',
        'Right dock → KAIRO Briefing for the short summary.',
      ]),
    };
  }

  if (input.runPhase === 'review_ready') {
    return {
      title: 'Review ready — read output, then complete',
      steps: withTerminalHint([
        'Read the Conversation panel (right) for command output — e.g. git status results.',
        'Center → COMPLETE RUN when the output looks good (one-shot commands do not need RESUME).',
        'For multi-step work only: RESUME RUN or type resume from review in Command.',
        'Left → Attention when signals still need review.',
      ]),
    };
  }

  if (input.runPhase === 'executing') {
    return {
      title: terminalVisible ? 'Run in progress' : 'Run in progress — open the terminal to follow shell output',
      steps: withTerminalHint([
        'Watch Mission Control live feed for step-by-step progress.',
        'CONTINUE RUN when the agent is idle but the task is unfinished (stuck execute).',
        'COMPLETE RUN only after review_ready — when the work unit is truly done.',
        'STOP RUN pauses execution; RESUME continues from paused.',
        'Send more work via right dock → Command (exact commands only).',
      ]),
    };
  }

  if (input.runPhase === 'paused') {
    return {
      title: 'Run paused — finish or continue',
      steps: withTerminalHint([
        'RESUME continues the run (EXECUTE phase).',
        'Another STOP while paused cancels the run entirely.',
        'COMPLETE RUN is available after the run reaches review_ready.',
      ]),
    };
  }

  if (input.runPhase === 'awaiting_approval') {
    return {
      title: 'Run waiting on approval',
      steps: withTerminalHint([
        'Open Attention (left) or KAIRO Briefing (right) for context.',
        'Use APPROVE RUN / REJECT RUN in Mission Control when ready.',
      ]),
    };
  }

  if (!input.hasActiveRun) {
    return {
      title: terminalVisible
        ? 'Idle — start with a workspace command'
        : 'Terminal hidden — reopen when you need shell output',
      steps: withTerminalHint([
        'Left sidebar → pick axon-watch or axon-local.',
        'Right dock → Command tab → try git status or health.',
        'Footer Commands lists every supported command with a Use button.',
        'Toggle IDE (top-right) when you need files, editor, or terminal.',
      ]),
    };
  }

  return null;
}
