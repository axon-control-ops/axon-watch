import type { RunRecord } from '../contracts/canonical';

/**
 * Show IDE stop only while the agent stream is live.
 * Idle/stuck executing runs offer Resume/Continue instead of Stop.
 */
export function shouldShowIdeAgentStop(input: {
  agentStreamActive: boolean;
  run: RunRecord | null | undefined;
}): boolean {
  void input.run;
  return input.agentStreamActive;
}

export function shouldClearIdeAgentRunLink(run: RunRecord | null | undefined): boolean {
  if (!run) {
    return true;
  }
  return run.phase === 'completed' || run.phase === 'failed' || run.phase === 'cancelled';
}
