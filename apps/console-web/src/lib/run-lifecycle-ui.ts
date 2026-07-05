import type { RunPhase } from '../contracts/canonical';

/** Phases where the operator can dismiss/close an active command run. */
export const OPERATOR_COMPLETABLE_PHASES: ReadonlySet<RunPhase> = new Set([
  'review_ready',
  'executing',
  'paused',
]);

export function isOperatorCompletablePhase(
  phase: RunPhase | null | undefined,
): boolean {
  return Boolean(phase && OPERATOR_COMPLETABLE_PHASES.has(phase));
}
