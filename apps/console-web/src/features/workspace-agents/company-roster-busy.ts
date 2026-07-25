import type { CompanyEmployeeRecord } from '../../contracts/canonical';

import { employeeFailureLine } from './company-roster-failure-view';
import { employeeStatusIsActivelyBusy } from './company-roster-status';

export function employeeIsLeadLikeRole(employee: CompanyEmployeeRecord): boolean {
  const role = (employee.role ?? '').trim().toLowerCase();
  return role === 'lead' || role === 'workspace_agent' || role === 'overview_agent';
}

/** True when the teammate is mid-shift (or has an active run), not merely on-duty watching. */
export function employeeIsActivelyBusy(employee: CompanyEmployeeRecord): boolean {
  if (employeeFailureLine(employee)) {
    return false;
  }
  if (!employee.enabled) {
    return false;
  }
  // Own role-tagged run is personal busy only once work has entered a mid-shift phase.
  // Lead fan-out leaves queued/assigned runs that must not light "N BUSY" with empty threads.
  if (employee.active_run_id?.trim()) {
    const status = (employee.status ?? '').trim();
    if (status === 'assigned' || status === 'watching' || status === 'idle') {
      return false;
    }
    return true;
  }
  // Lead status mirrors *any* workspace run for management UX — that must not
  // light Lead's avatar while a specialist (e.g. Soren) is the one working.
  if (employeeIsLeadLikeRole(employee)) {
    return false;
  }
  return employeeStatusIsActivelyBusy(employee.status);
}

export function companyBusyEmployees(
  employees: readonly CompanyEmployeeRecord[] | null | undefined,
): CompanyEmployeeRecord[] {
  return (employees ?? []).filter((row) => employeeIsActivelyBusy(row));
}

export function companyBusyEmployeesCount(
  employees: readonly CompanyEmployeeRecord[] | null | undefined,
): number {
  return companyBusyEmployees(employees).length;
}
