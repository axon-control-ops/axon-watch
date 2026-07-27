export type AgentDockAutoPeekInput = {
  layoutMode: 'operator' | 'ide';
  agentDockCollapsed: boolean;
  pendingApprovals: number;
  lastPeekedApprovalCount: number;
};

export type AgentDockStreamingAutoPeekInput = {
  layoutMode: 'operator' | 'ide';
  agentDockCollapsed: boolean;
  streaming: boolean;
  streamMessageId: string | null;
  alreadyPeekedStreamMessageIds: ReadonlySet<string>;
};

/** Expand the agent dock when new approvals arrive while it is collapsed in IDE mode. */
export function shouldAutoPeekAgentDock(input: AgentDockAutoPeekInput): boolean {
  if (input.layoutMode !== 'ide' || !input.agentDockCollapsed) {
    return false;
  }

  if (input.pendingApprovals <= 0) {
    return false;
  }

  return input.pendingApprovals > input.lastPeekedApprovalCount;
}

/**
 * Streaming no longer auto-expands the dock — IDE stays quiet while coding.
 * Status-bar / AGENT strip pulse carries live attention instead.
 */
export function shouldAutoPeekAgentDockForStreaming(
  _input: AgentDockStreamingAutoPeekInput,
): boolean {
  return false;
}

export type AgentDockRunAutoPeekInput = {
  layoutMode: 'operator' | 'ide';
  agentDockCollapsed: boolean;
  runPhase: string | null;
  runId: string | null;
  alreadyPeekedRunIds: ReadonlySet<string>;
};

/**
 * Run-phase peeks disabled — executing / review_ready pulse the AGENT chip instead.
 * Approvals and teammate failures still auto-peek via their dedicated helpers.
 */
export function shouldAutoPeekAgentDockForRun(
  _input: AgentDockRunAutoPeekInput,
): boolean {
  return false;
}

export type AgentDockEmployeeFailureAutoPeekInput = {
  layoutMode: 'operator' | 'ide';
  agentDockCollapsed: boolean;
  employeeFailureLine: string | null;
  employeeFailurePeekKey: string | null;
  agentStreamActive: boolean;
  alreadyPeekedFailureKeys: ReadonlySet<string>;
};

/** Expand the agent dock once when a teammate shift fails while the dock is collapsed. */
export function shouldAutoPeekAgentDockForEmployeeFailure(
  input: AgentDockEmployeeFailureAutoPeekInput,
): boolean {
  if (input.layoutMode !== 'ide' || !input.agentDockCollapsed) {
    return false;
  }

  if (input.agentStreamActive) {
    return false;
  }

  const peekKey = input.employeeFailurePeekKey?.trim() ?? '';
  if (!peekKey || !input.employeeFailureLine) {
    return false;
  }

  return !input.alreadyPeekedFailureKeys.has(peekKey);
}
