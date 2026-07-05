export type OperatorQuickGuide = {
  title: string;
  steps: string[];
};

export function buildOperatorQuickGuide(input: {
  runPhase: string | null;
  hasActiveRun: boolean;
  pendingApprovals: number;
  layoutMode: 'operator' | 'ide';
}): OperatorQuickGuide | null {
  if (input.layoutMode !== 'operator') {
    return null;
  }

  if (input.pendingApprovals > 0) {
    return {
      title: 'Approval waiting — decide before more work runs',
      steps: [
        'Center Mission Control → APPROVE RUN or REJECT RUN.',
        'Left sidebar → Attention to read why approval was requested.',
        'Right dock → KAIRO Briefing for the short summary.',
      ],
    };
  }

  if (input.runPhase === 'review_ready') {
    return {
      title: 'Review ready — the run paused for you',
      steps: [
        'Read the Conversation panel (right) for command output — e.g. git status results.',
        'Center → RESUME RUN to continue, or COMPLETE RUN if the output looks good.',
        'Or right dock → Command tab → type resume from review (or footer Commands → Use).',
        'Left → Attention when signals still need review.',
      ],
    };
  }

  if (input.runPhase === 'executing') {
    return {
      title: 'Run in progress',
      steps: [
        'Watch Mission Control live feed for step-by-step progress.',
        'COMPLETE RUN when output looks good — you do not need to wait for review_ready.',
        'STOP RUN pauses execution; COMPLETE still available while paused or executing.',
        'Send more work via right dock → Command (exact commands only).',
      ],
    };
  }

  if (input.runPhase === 'paused') {
    return {
      title: 'Run paused — finish or continue',
      steps: [
        'RESUME continues the run (EXECUTE phase).',
        'COMPLETE RUN closes it — use this when you are done reviewing output.',
        'Another STOP while paused cancels the run entirely.',
      ],
    };
  }

  if (input.runPhase === 'awaiting_approval') {
    return {
      title: 'Run waiting on approval',
      steps: [
        'Open Attention (left) or KAIRO Briefing (right) for context.',
        'Use APPROVE RUN / REJECT RUN in Mission Control when ready.',
      ],
    };
  }

  if (!input.hasActiveRun) {
    return {
      title: 'Idle — start with a workspace command',
      steps: [
        'Left sidebar → pick axon-watch or axon-local.',
        'Right dock → Command tab → try git status or health.',
        'Footer Commands lists every supported command with a Use button.',
        'Toggle IDE (top-right) when you need files, editor, or terminal.',
      ],
    };
  }

  return null;
}
