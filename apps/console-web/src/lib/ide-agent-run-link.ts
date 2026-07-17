import type { RunRecord } from '../contracts/canonical';

import type { OperatorThreadEntry } from './operator-thread';

const IDE_AGENT_LINK_PHASES = new Set([
  'queued',
  'starting',
  'planning',
  'awaiting_approval',
  'executing',
  'paused',
  'review_ready',
]);

export type ResolveIdeAgentLinkedRunOptions = {
  /** When set, only link to a run whose mode matches (e.g. debug vs agent). */
  expectedMode?: string | null;
};

/** Run id to attach the next IDE Agent/Debug/Plan composer turn to (Lane B only). */
export function resolveIdeAgentLinkedRunId(
  storedRunId: string | null,
  runs: RunRecord[],
  options: ResolveIdeAgentLinkedRunOptions = {},
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
  const expected = String(options.expectedMode || '').trim().toLowerCase();
  if (expected && String(linked.mode || '').trim().toLowerCase() !== expected) {
    return null;
  }
  return storedRunId;
}

export function resolveIdeAgentLinkedRunIdFromMessages(
  messages: OperatorThreadEntry[],
  runs: RunRecord[],
  options: ResolveIdeAgentLinkedRunOptions = {},
): string | null {
  for (let index = messages.length - 1; index >= 0; index -= 1) {
    const runId = messages[index]?.run_id ?? null;
    const resolved = resolveIdeAgentLinkedRunId(runId, runs, options);
    if (resolved) {
      return resolved;
    }
  }
  return null;
}
