import { fetchJson } from './client';
import type { TeammateRouteDecision, TeammateRouteEmployee } from '../lib/composer-teammate-route';

export type RouteTeammateRequest = {
  prompt: string;
  current_employee_id?: string | null;
  use_model_tiebreak?: boolean;
};

export type RouteTeammateResponse = {
  should_route: boolean;
  reason: string;
  employee_id: string | null;
  employee_role: string | null;
  employee_name: string | null;
  employee_role_label: string | null;
  employee_owns: string | null;
  from_employee_id: string | null;
  from_name: string | null;
  winner_score: number | null;
  second_score: number | null;
  source: 'deterministic' | 'model';
  ambiguous: boolean;
  routing_receipt: string | null;
  model_receipt: Record<string, unknown> | null;
};

export async function postRouteTeammate(
  workspaceId: string,
  body: RouteTeammateRequest,
): Promise<RouteTeammateResponse> {
  const encoded = encodeURIComponent(workspaceId);
  return fetchJson<RouteTeammateResponse>(
    `/api/workspaces/${encoded}/company/route-teammate`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    },
    'route teammate request failed',
    45_000,
  );
}

export function routeTeammateResponseToDecision(
  response: RouteTeammateResponse,
  roster: readonly TeammateRouteEmployee[],
): TeammateRouteDecision {
  const employeeId = response.employee_id?.trim() ?? '';
  const fromRoster = employeeId
    ? roster.find((row) => row.employee_id.trim() === employeeId)
    : undefined;
  const employee: TeammateRouteEmployee | undefined = fromRoster
    ? fromRoster
    : employeeId
      ? {
          employee_id: employeeId,
          name: response.employee_name?.trim() || 'teammate',
          role: response.employee_role?.trim() || 'workspace_agent',
          role_label: response.employee_role_label?.trim() || response.employee_role || 'role',
          owns: response.employee_owns?.trim() || '',
        }
      : undefined;

  return {
    shouldRoute: Boolean(response.should_route) && Boolean(employee),
    reason: response.reason,
    employee,
    fromEmployeeId: response.from_employee_id ?? undefined,
    fromName: response.from_name ?? undefined,
    winnerScore: response.winner_score ?? undefined,
    secondScore: response.second_score ?? undefined,
    source: response.source,
    ambiguous: Boolean(response.ambiguous),
    routingReceipt: response.routing_receipt,
    modelReceipt: response.model_receipt,
  };
}
