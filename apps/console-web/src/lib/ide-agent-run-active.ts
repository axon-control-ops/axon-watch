import type { RunRecord } from '../contracts/canonical';

const LIVE_STOP_PHASES = new Set(['queued', 'starting', 'planning', 'executing']);

/** Show IDE stop only while the agent is actively running, not after the lane goes idle. */
export function shouldShowIdeAgentStop(input: {
  agentStreamActive: boolean;
  run: RunRecord | null | undefined;
}): boolean {
  if (input.agentStreamActive) {
    return true;
  }

  const run = input.run;
  if (!run?.can_stop) {
    return false;
  }

  if (!LIVE_STOP_PHASES.has(run.phase)) {
    return false;
  }

  return run.status === 'running';
}

export function shouldClearIdeAgentRunLink(run: RunRecord | null | undefined): boolean {
  if (!run) {
    return true;
  }
  return run.phase === 'completed' || run.phase === 'failed' || run.phase === 'cancelled';
}
