/** Decide when IDE stream chrome is stale after run refresh / CP bounce. */

const TERMINAL_RUN_PHASES = new Set(['completed', 'failed', 'cancelled']);

export type StaleIdeStreamSettleDecision = 'keep' | 'settle';

export function decideStaleIdeStreamSettle(input: {
  active: boolean;
  hasLiveSession: boolean;
  ideAgentRunId: string | null | undefined;
  /** Run phase when run id is known; null means the run is missing from the loaded list. */
  runPhase: string | null | undefined;
  runsLoaded: boolean;
}): StaleIdeStreamSettleDecision {
  if (!input.active) {
    return 'keep';
  }

  // UI says streaming but EventSource is gone (common after control-plane bounce).
  if (!input.hasLiveSession) {
    return 'settle';
  }

  const runId = String(input.ideAgentRunId ?? '').trim();
  if (!runId) {
    // Ask/plan streams can be live without a run link.
    return 'keep';
  }

  if (!input.runsLoaded) {
    return 'keep';
  }

  const phase = input.runPhase == null ? null : String(input.runPhase).trim();
  if (!phase || TERMINAL_RUN_PHASES.has(phase)) {
    return 'settle';
  }

  return 'keep';
}

export function listStaleIdeStreamThreadIds(input: {
  streamUiByThreadId: Record<
    string,
    {
      active: boolean;
      ideAgentRunId: string | null;
    }
  >;
  liveSessionThreadIds: ReadonlySet<string> | Iterable<string>;
  runPhaseById: Record<string, string | undefined> | Map<string, string | undefined>;
  runsLoaded: boolean;
}): string[] {
  const live =
    input.liveSessionThreadIds instanceof Set
      ? input.liveSessionThreadIds
      : new Set(input.liveSessionThreadIds);
  const phaseOf = (runId: string): string | null | undefined => {
    if (input.runPhaseById instanceof Map) {
      return input.runPhaseById.has(runId) ? input.runPhaseById.get(runId) : null;
    }
    return Object.prototype.hasOwnProperty.call(input.runPhaseById, runId)
      ? input.runPhaseById[runId]
      : null;
  };

  const stale: string[] = [];
  for (const [threadId, state] of Object.entries(input.streamUiByThreadId)) {
    const runId = state.ideAgentRunId;
    const decision = decideStaleIdeStreamSettle({
      active: state.active,
      hasLiveSession: live.has(threadId),
      ideAgentRunId: runId,
      runPhase: runId ? phaseOf(runId) : null,
      runsLoaded: input.runsLoaded,
    });
    if (decision === 'settle') {
      stale.push(threadId);
    }
  }
  return stale;
}
