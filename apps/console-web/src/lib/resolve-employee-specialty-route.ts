/**
 * Resolve specialty route: deterministic first, optional server model tie-break.
 */

import {
  postRouteTeammate,
  routeTeammateResponseToDecision,
} from '../api/company-route-api';
import {
  isAmbiguousTeammateRoute,
  shouldSoftRouteToTeammate,
  type TeammateRouteDecision,
  type TeammateRouteEmployee,
} from './composer-teammate-route';

export async function resolveEmployeeSpecialtyRoute(input: {
  prompt: string;
  workspaceId: string;
  currentEmployee: TeammateRouteEmployee | null | undefined;
  roster: readonly TeammateRouteEmployee[];
  useModelTiebreak?: boolean;
}): Promise<TeammateRouteDecision> {
  const startedAt = Date.now();
  const local = shouldSoftRouteToTeammate(
    input.prompt,
    input.currentEmployee,
    input.roster,
  );
  // #region agent log
  {
    const promptLower = input.prompt.toLowerCase();
    const fanOutIntent =
      /\b(all|every|each)\b/.test(promptLower) &&
      /\b(sub[- ]?agents?|teammates?|employees?|agents?|team)\b/.test(promptLower);
    fetch('http://127.0.0.1:7706/ingest/90bcaec2-2b39-4d4a-84b5-157c12735440', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Debug-Session-Id': 'fc0b35',
      },
      body: JSON.stringify({
        sessionId: 'fc0b35',
        runId: 'send-delay',
        hypothesisId: 'H8a',
        location: 'resolve-employee-specialty-route.ts:local',
        message: 'specialty route local decision',
        data: {
          fanOutIntent,
          elapsedMs: Date.now() - startedAt,
          useModelTiebreak: Boolean(input.useModelTiebreak),
          localShouldRoute: local.shouldRoute,
          localReason: local.reason,
          localAmbiguous: Boolean(local.ambiguous),
          willAwaitTiebreak:
            !local.shouldRoute &&
            Boolean(input.useModelTiebreak) &&
            isAmbiguousTeammateRoute(local),
          localWinnerName: local.employee?.name ?? null,
          promptPreview: input.prompt.slice(0, 120),
        },
        timestamp: Date.now(),
      }),
    }).catch(() => {});
  }
  // #endregion
  if (local.shouldRoute) {
    return local;
  }
  if (!input.useModelTiebreak) {
    return local;
  }
  if (!isAmbiguousTeammateRoute(local)) {
    return local;
  }
  const workspaceId = input.workspaceId.trim();
  if (!workspaceId) {
    return local;
  }

  try {
    const tiebreakStartedAt = Date.now();
    const response = await postRouteTeammate(workspaceId, {
      prompt: input.prompt,
      current_employee_id: input.currentEmployee?.employee_id ?? null,
      use_model_tiebreak: true,
    });
    const decision = routeTeammateResponseToDecision(response, input.roster);
    // #region agent log
    fetch('http://127.0.0.1:7706/ingest/90bcaec2-2b39-4d4a-84b5-157c12735440', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Debug-Session-Id': 'fc0b35',
      },
      body: JSON.stringify({
        sessionId: 'fc0b35',
        runId: 'send-delay',
        hypothesisId: 'H8a',
        location: 'resolve-employee-specialty-route.ts:tiebreak',
        message: 'model tiebreak completed',
        data: {
          tiebreakMs: Date.now() - tiebreakStartedAt,
          totalMs: Date.now() - startedAt,
          shouldRoute: decision.shouldRoute,
          reason: decision.reason,
          source: decision.source,
          winnerName: decision.employee?.name ?? null,
        },
        timestamp: Date.now(),
      }),
    }).catch(() => {});
    // #endregion
    return decision;
  } catch {
    // #region agent log
    fetch('http://127.0.0.1:7706/ingest/90bcaec2-2b39-4d4a-84b5-157c12735440', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Debug-Session-Id': 'fc0b35',
      },
      body: JSON.stringify({
        sessionId: 'fc0b35',
        runId: 'send-delay',
        hypothesisId: 'H8a',
        location: 'resolve-employee-specialty-route.ts:tiebreak-error',
        message: 'model tiebreak failed/timed out',
        data: { totalMs: Date.now() - startedAt },
        timestamp: Date.now(),
      }),
    }).catch(() => {});
    // #endregion
    return local;
  }
}
