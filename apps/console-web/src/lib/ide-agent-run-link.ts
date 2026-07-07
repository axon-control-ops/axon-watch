import type { RunRecord } from '../contracts/canonical';

import type { OperatorThreadEntry } from './operator-thread';

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

export function resolveIdeAgentLinkedRunIdFromMessages(
  messages: OperatorThreadEntry[],
  runs: RunRecord[],
): string | null {
  for (let index = messages.length - 1; index >= 0; index -= 1) {
    const runId = messages[index]?.run_id ?? null;
    const resolved = resolveIdeAgentLinkedRunId(runId, runs);
    if (resolved) {
      return resolved;
    }
  }
  return null;
}
