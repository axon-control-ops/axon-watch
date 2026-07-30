/** Decide when IDE stream chrome is stale after run refresh / CP bounce. */

const TERMINAL_RUN_PHASES = new Set(['completed', 'failed', 'cancelled']);
const BUSY_RUN_PHASES = new Set(['executing', 'starting', 'planning', 'queued']);

export type StaleIdeStreamSettleDecision = 'keep' | 'settle' | 'reattach';

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

  const runId = String(input.ideAgentRunId ?? '').trim();
  const phase = input.runPhase == null ? null : String(input.runPhase).trim();

  // UI says streaming but EventSource is gone.
  if (!input.hasLiveSession) {
    // Linked run is still busy — keep chrome and signal a reconnect, do not clear.
    if (runId && input.runsLoaded && phase && BUSY_RUN_PHASES.has(phase)) {
      return 'reattach';
    }
    // Ask/plan with no run link and no socket — orphaned chrome.
    if (!runId) {
      return 'settle';
    }
    if (!input.runsLoaded) {
      return 'keep';
    }
    if (!phase || TERMINAL_RUN_PHASES.has(phase)) {
      return 'settle';
    }
    // Unknown mid-flight phase — prefer reconnect over dropping the operator link.
    return 'reattach';
  }

  if (!runId) {
    // Ask/plan streams can be live without a run link.
    return 'keep';
  }

  if (!input.runsLoaded) {
    return 'keep';
  }

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
  return listIdeStreamUiDecisions(input)
    .filter((item) => item.decision === 'settle')
    .map((item) => item.threadId);
}

export function listReattachIdeStreamThreadIds(input: {
  streamUiByThreadId: Record<
    string,
    {
      active: boolean;
      ideAgentRunId: string | null;
      messageId?: string | null;
    }
  >;
  liveSessionThreadIds: ReadonlySet<string> | Iterable<string>;
  runPhaseById: Record<string, string | undefined> | Map<string, string | undefined>;
  runsLoaded: boolean;
}): string[] {
  return listIdeStreamUiDecisions(input)
    .filter((item) => item.decision === 'reattach')
    .map((item) => item.threadId);
}

function listIdeStreamUiDecisions(input: {
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
}): Array<{ threadId: string; decision: StaleIdeStreamSettleDecision }> {
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

  const decisions: Array<{ threadId: string; decision: StaleIdeStreamSettleDecision }> = [];
  for (const [threadId, state] of Object.entries(input.streamUiByThreadId)) {
    const runId = state.ideAgentRunId;
    const decision = decideStaleIdeStreamSettle({
      active: state.active,
      hasLiveSession: live.has(threadId),
      ideAgentRunId: runId,
      runPhase: runId ? phaseOf(runId) : null,
      runsLoaded: input.runsLoaded,
    });
    if (decision !== 'keep') {
      decisions.push({ threadId, decision });
    }
  }
  return decisions;
}
