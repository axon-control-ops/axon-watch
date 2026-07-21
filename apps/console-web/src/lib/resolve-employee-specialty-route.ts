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
  const local = shouldSoftRouteToTeammate(
    input.prompt,
    input.currentEmployee,
    input.roster,
  );
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
    const response = await postRouteTeammate(workspaceId, {
      prompt: input.prompt,
      current_employee_id: input.currentEmployee?.employee_id ?? null,
      use_model_tiebreak: true,
    });
    return routeTeammateResponseToDecision(response, input.roster);
  } catch {
    return local;
  }
}
