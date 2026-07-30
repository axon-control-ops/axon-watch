import {
  applyEmployeeSpecialtyRoute,
  type ApplySpecialtyRouteResult,
  type SpecialtyRouteShell,
} from './apply-employee-specialty-route';
import type {
  TeammateRouteDecision,
  TeammateRouteEmployee,
} from './composer-teammate-route';
import {
  matchNamedAssignEmployee,
  rewriteNamedAssignPrompt,
} from './named-assign-route';
import { resolveEmployeeSpecialtyRoute } from './resolve-employee-specialty-route';
import { clearTeammateRouteNotice } from './teammate-route-notice';

export type RouteEmployeeSpecialtyTaskResult = {
  decision: TeammateRouteDecision;
  applied: ApplySpecialtyRouteResult;
  submitted: boolean;
};

/**
 * Shared Brain/handoff sequence. The owning thread is opened before the task is
 * restored and submitted; a failed route never prevents the generic submit.
 */
export async function routeEmployeeSpecialtyTask(input: {
  shell: SpecialtyRouteShell;
  prompt: string;
  workspaceId: string;
  currentEmployee: TeammateRouteEmployee | null;
  roster: readonly TeammateRouteEmployee[];
  preferredEmployeeId?: string;
  restorePrompt: (prompt: string) => void;
  submit?: () => Promise<void>;
}): Promise<RouteEmployeeSpecialtyTaskResult> {
  clearTeammateRouteNotice();
  const preferred = input.preferredEmployeeId
    ? input.roster.find((employee) => employee.employee_id === input.preferredEmployeeId)
    : undefined;
  const decision: TeammateRouteDecision = preferred
    ? {
        shouldRoute: preferred.employee_id !== input.currentEmployee?.employee_id,
        reason: `brain_${preferred.role}`,
        employee: preferred,
        fromEmployeeId: input.currentEmployee?.employee_id,
        fromName: input.currentEmployee?.name ?? 'workspace',
        source: 'model',
      }
    : await resolveEmployeeSpecialtyRoute({
        prompt: input.prompt,
        workspaceId: input.workspaceId,
        currentEmployee: input.currentEmployee,
        roster: input.roster,
        useModelTiebreak: true,
      });

  const applied = await applyEmployeeSpecialtyRoute(input.shell, decision);
  const namedAssign = matchNamedAssignEmployee(input.prompt, input.roster);
  const shouldRewrite =
    Boolean(namedAssign) &&
    (applied.routed ||
      (decision.reason === 'already_owning' &&
        decision.employee?.employee_id === namedAssign?.employee.employee_id));
  const promptForSubmit =
    shouldRewrite && namedAssign
      ? rewriteNamedAssignPrompt(input.prompt, namedAssign.employee.name)
      : input.prompt;
  input.restorePrompt(promptForSubmit);
  if (input.submit) {
    await input.submit();
  }
  return { decision, applied, submitted: Boolean(input.submit) };
}
