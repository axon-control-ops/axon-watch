/**
 * Soft specialty routing must not yank a send onto a teammate who is already
 * mid-stream/busy — that queues or blocks the prompt and the origin tab looks
 * like "won't start". Explicit named assigns still follow the operator target.
 */

export type SpecialtyRouteBusyGateDecision = {
  shouldRoute: boolean;
  reason: string;
  employee?: { employee_id: string } | null;
};

export function isNamedAssignSpecialtyRoute(reason: string): boolean {
  return reason.startsWith('named_assign');
}

export function shouldApplySpecialtyRouteNow(input: {
  decision: SpecialtyRouteBusyGateDecision;
  busyEmployeeIds: readonly string[];
}): boolean {
  if (!input.decision.shouldRoute || !input.decision.employee) {
    return false;
  }
  if (isNamedAssignSpecialtyRoute(input.decision.reason)) {
    return true;
  }
  const destinationId = input.decision.employee.employee_id.trim();
  if (!destinationId) {
    return false;
  }
  const busy = new Set(
    input.busyEmployeeIds.map((id) => id.trim()).filter(Boolean),
  );
  return !busy.has(destinationId);
}
