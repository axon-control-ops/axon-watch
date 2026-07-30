/**
 * Plain-English Team dock talk beats (status + delivery handoff).
 */

import type { CompanyEmployeeRecord } from '../../contracts/canonical';

import { employeeFailureDetailTooltip, employeeFailureLine } from './company-roster-failure-view';
import { employeeIsWorking } from './company-roster-status';
import {
  employeeDeliveryDetailTooltip,
  humanizeEmployeeDeliveryHandoff,
} from './employee-delivery-handoff-view';

const HANDOFF_ROLES = new Set(['watcher', 'integrations', 'lead', 'backend']);

export function employeeTalkLine(employee: CompanyEmployeeRecord): string | null {
  const failure = employeeFailureLine(employee);
  if (failure) {
    return failure;
  }
  const role = String(employee.role || '').toLowerCase();
  if (HANDOFF_ROLES.has(role)) {
    const handoff = humanizeEmployeeDeliveryHandoff({
      stage: employee.pipeline_stage,
      detail: employee.pipeline_detail,
      draftPrUrl: employee.draft_pr_url,
      ciStatus: employee.ci_status,
    });
    if (handoff) {
      return handoff;
    }
  }
  if (!employeeIsWorking(employee.status)) {
    return null;
  }
  const owns = employee.owns?.trim() || employee.role_label?.trim() || 'my lane';
  const status = (employee.status ?? '').trim();
  if (status === 'watching') {
    return `Watching ${owns} for new signals.`;
  }
  if (status === 'planning') {
    return `Planning the next cut on ${owns}.`;
  }
  if (status === 'executing') {
    return `In progress on ${owns}.`;
  }
  if (status === 'verifying') {
    return `Verifying ${owns} before handoff.`;
  }
  if (status === 'blocked') {
    return `Blocked on ${owns} — need a decision.`;
  }
  if (status === 'waiting_approval') {
    return `Waiting on approval for ${owns}.`;
  }
  if (status === 'handoff_ready') {
    return `Ready to hand off ${owns}.`;
  }
  return `On ${owns}.`;
}

/** Hover/tooltip for the Team dock beat when a delivery handoff is shown. */
export function employeeTalkLineDetailTooltip(
  employee: CompanyEmployeeRecord,
): string | null {
  if (employeeFailureLine(employee)) {
    return employeeFailureDetailTooltip(employee);
  }
  const role = String(employee.role || '').toLowerCase();
  if (!HANDOFF_ROLES.has(role)) {
    return null;
  }
  return employeeDeliveryDetailTooltip({
    stage: employee.pipeline_stage,
    detail: employee.pipeline_detail,
    draftPrUrl: employee.draft_pr_url,
    ciStatus: employee.ci_status,
  });
}
