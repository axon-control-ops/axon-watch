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

/** Expand the agent dock once per stream when the agent starts responding in IDE mode. */
export function shouldAutoPeekAgentDockForStreaming(
  input: AgentDockStreamingAutoPeekInput,
): boolean {
  if (input.layoutMode !== 'ide' || !input.agentDockCollapsed || !input.streaming) {
    return false;
  }

  const messageId = input.streamMessageId?.trim() ?? '';
  if (!messageId) {
    return false;
  }

  return !input.alreadyPeekedStreamMessageIds.has(messageId);
}

export type AgentDockRunAutoPeekInput = {
  layoutMode: 'operator' | 'ide';
  agentDockCollapsed: boolean;
  runPhase: string | null;
  runId: string | null;
  alreadyPeekedRunIds: ReadonlySet<string>;
};

const AUTO_PEEK_RUN_PHASES = new Set(['executing', 'review_ready']);

/** Expand the agent dock once per run when IDE work needs the conversation panel. */
export function shouldAutoPeekAgentDockForRun(input: AgentDockRunAutoPeekInput): boolean {
  if (input.layoutMode !== 'ide' || !input.agentDockCollapsed) {
    return false;
  }

  const runId = input.runId?.trim() ?? '';
  const phase = input.runPhase ?? '';
  if (!runId || !AUTO_PEEK_RUN_PHASES.has(phase)) {
    return false;
  }

  return !input.alreadyPeekedRunIds.has(runId);
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
