import type { RunRecord } from '../contracts/canonical';

const IDE_AGENT_LINK_PHASES = new Set(['awaiting_approval', 'executing', 'paused', 'review_ready']);

/** Run id to attach the next IDE Agent composer turn to (Lane B only). */
export function resolveIdeAgentLinkedRunId(
  storedRunId: string | null,
  runs: RunRecord[],
): string | null {
  if (!storedRunId) {
    return null;
  }
  const linked = runs.find((run) => run.run_id === storedRunId);
  if (!linked) {
    return null;
  }
  if (!IDE_AGENT_LINK_PHASES.has(linked.phase)) {
    return null;
  }
  return storedRunId;
}
