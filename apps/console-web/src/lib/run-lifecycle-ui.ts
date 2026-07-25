import type { RunRecord } from '../contracts/canonical';

type RunPhase = RunRecord['phase'];
type RunMode = RunRecord['mode'];

/**
 * Phases where the operator can dismiss/close an active run.
 * Only review_ready means the work unit is truly done awaiting operator close.
 */
export const OPERATOR_COMPLETABLE_PHASES: ReadonlySet<RunPhase> = new Set([
  'review_ready',
]);

export function isOperatorCompletablePhase(
  phase: RunPhase | null | undefined,
): boolean {
  return Boolean(phase && OPERATOR_COMPLETABLE_PHASES.has(phase));
}

/**
 * Stuck agent execute with no live stream — CONTINUE can re-dispatch work.
 * Non-agent idle execute is not continuable via resume APIs alone (stop→resume
 * only flips phase and does not restart command work).
 */
export function isIdleIncompleteExecutingRun(input: {
  phase: RunPhase | null | undefined;
  agentStreamActive: boolean;
  mode?: RunMode | null;
}): boolean {
  if (input.phase !== 'executing' || input.agentStreamActive) {
    return false;
  }
  if (input.mode != null && input.mode !== 'agent' && input.mode !== 'debug') {
    return false;
  }
  return true;
}

/** Offer CONTINUE/RESUME when the run is incomplete and can be progressed. */
export function shouldOfferRunContinue(input: {
  phase: RunPhase | null | undefined;
  canResume: boolean;
  agentStreamActive: boolean;
  mode?: RunMode | null;
}): boolean {
  if (input.canResume) {
    return true;
  }
  return isIdleIncompleteExecutingRun({
    phase: input.phase,
    agentStreamActive: input.agentStreamActive,
    mode: input.mode,
  });
}

/** Mission Control / IDE label: CONTINUE for idle execute, RESUME otherwise. */
export function runContinueActionLabel(input: {
  phase: RunPhase | null | undefined;
  agentStreamActive: boolean;
  mode?: RunMode | null;
  pending?: boolean;
  pendingLabel?: string;
  continueLabel?: string;
  resumeLabel?: string;
}): string {
  if (input.pending) {
    return input.pendingLabel ?? 'RESUMING…';
  }
  if (
    isIdleIncompleteExecutingRun({
      phase: input.phase,
      agentStreamActive: input.agentStreamActive,
      mode: input.mode ?? 'agent',
    })
  ) {
    return input.continueLabel ?? 'CONTINUE';
  }
  return input.resumeLabel ?? 'RESUME';
}

/** Resolve the operator prompt to re-dispatch when continuing an agent run. */
export function resolveAgentContinuePrompt(input: {
  runId: string;
  runSummary?: string | null;
  ideMessages: ReadonlyArray<{ role: string; run_id?: string | null; content: string }>;
  operatorMessages?: ReadonlyArray<{
    role: string;
    run_id?: string | null;
    content: string;
  }>;
}): string | null {
  const targetRunId = input.runId.trim();
  const pools = [input.ideMessages, input.operatorMessages ?? []];
  for (const messages of pools) {
    for (let index = messages.length - 1; index >= 0; index -= 1) {
      const message = messages[index];
      if (
        message?.role === 'operator' &&
        String(message.run_id ?? '').trim() === targetRunId &&
        message.content.trim()
      ) {
        return message.content.trim();
      }
    }
  }
  for (const messages of pools) {
    for (let index = messages.length - 1; index >= 0; index -= 1) {
      const message = messages[index];
      if (message?.role === 'operator' && message.content.trim()) {
        return message.content.trim();
      }
    }
  }
  const summary = String(input.runSummary ?? '').trim();
  return summary || null;
}
