export type AgentDockReopenState = {
  streaming: boolean;
  pendingApprovals: number;
  runPhase: string | null;
};

function approvalPhrase(count: number): string {
  return `${count} approval${count === 1 ? '' : 's'} waiting`;
}

/** Tooltip for the collapsed agent-dock reopen strip. */
export function agentDockReopenTitle(state: AgentDockReopenState): string {
  return ['Expand agent dock (Ctrl/Cmd+\\)', ...activityHintParts(state)].join(' · ');
}

/** Tooltip for the expanded agent-dock collapse control. */
export function agentDockCollapseTitle(): string {
  return 'Collapse agent dock (Ctrl/Cmd+\\)';
}

/** Accessible name for the collapsed agent-dock reopen strip. */
export function agentDockReopenAriaLabel(state: AgentDockReopenState): string {
  return ['Expand agent dock', ...activityAriaHintParts(state)].join(', ');
}

function runPhaseHintParts(runPhase: string | null): string[] {
  if (runPhase === 'executing') {
    return ['Run in progress'];
  }
  if (runPhase === 'review_ready') {
    return ['Review ready'];
  }
  return [];
}

function runPhaseAriaHintParts(runPhase: string | null): string[] {
  if (runPhase === 'executing') {
    return ['run in progress'];
  }
  if (runPhase === 'review_ready') {
    return ['review ready'];
  }
  return [];
}

function activityHintParts(state: AgentDockReopenState): string[] {
  const parts: string[] = [];
  if (state.streaming) {
    parts.push('Agent is responding');
  }
  if (state.pendingApprovals > 0) {
    parts.push(approvalPhrase(state.pendingApprovals));
  }
  if (!state.streaming && state.pendingApprovals <= 0) {
    parts.push(...runPhaseHintParts(state.runPhase));
  }
  return parts;
}

function activityAriaHintParts(state: AgentDockReopenState): string[] {
  const parts: string[] = [];
  if (state.streaming) {
    parts.push('agent is responding');
  }
  if (state.pendingApprovals > 0) {
    parts.push(approvalPhrase(state.pendingApprovals));
  }
  if (!state.streaming && state.pendingApprovals <= 0) {
    parts.push(...runPhaseAriaHintParts(state.runPhase));
  }
  return parts;
}

/** Tooltip for the IDE activity-bar agent button. */
export function agentDockActivityBarTitle(
  state: AgentDockReopenState,
  expanded: boolean,
): string {
  const parts = [
    expanded
      ? 'Agent dock (Ctrl/Cmd+\\) · Click to collapse'
      : 'Agent dock (Ctrl/Cmd+\\)',
  ];
  parts.push(...activityHintParts(state));
  return parts.join(' · ');
}

/** Accessible name for the IDE activity-bar agent button. */
export function agentDockActivityBarAriaLabel(
  state: AgentDockReopenState,
  expanded: boolean,
): string {
  return [
    expanded ? 'Collapse agent dock' : 'Expand agent dock',
    ...activityAriaHintParts(state),
  ].join(', ');
}

/** Whether the collapsed agent dock should show a live-attention treatment. */
export function agentDockReopenAlive(state: AgentDockReopenState): boolean {
  if (state.streaming || state.pendingApprovals > 0) {
    return true;
  }

  const phase = state.runPhase ?? '';
  return phase === 'executing' || phase === 'review_ready';
}
