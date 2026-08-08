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
  // Own role-tagged run is personal busy once dispatched. Continuous workers often
  // stay `watching` with an active_run_id while the IDE stream is live — count them.
  // Lead fan-out `assigned` (queued, not started) must not light "N BUSY".
  if (employee.active_run_id?.trim()) {
    const status = (employee.status ?? '').trim();
    if (status === 'assigned' || status === 'idle') {
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

export type ReportingEmployeeResolutionInput = {
  agentStreamActive: boolean;
  /** Employee owning the currently-focused IDE thread, when a stream is live. */
  activeThreadEmployeeId?: string | null;
  /** Thread ids with an active IDE chat stream (including background tabs). */
  streamingThreadIds?: readonly string[] | null;
  threads?: readonly { thread_id: string; employee_id?: string | null }[] | null;
};

/**
 * The single employee (if any) whose thread has live text streaming in right
 * now — narrower than "busy" (which also covers queued/mid-shift-but-quiet
 * work). This is the signal that expands that teammate's persona-dock card
 * over the roster grid so the operator can read the report without the
 * roster competing for space, then collapses back once the stream ends.
 */
export function resolveReportingEmployeeId(
  input: ReportingEmployeeResolutionInput,
): string | null {
  const focused = input.activeThreadEmployeeId?.trim();
  if (input.agentStreamActive && focused) {
    return focused;
  }
  const streaming = new Set(
    (input.streamingThreadIds ?? []).map((id) => id.trim()).filter(Boolean),
  );
  if (streaming.size && input.threads?.length) {
    for (const thread of input.threads) {
      const employeeId = thread.employee_id?.trim();
      if (streaming.has(thread.thread_id) && employeeId) {
        return employeeId;
      }
    }
  }
  return null;
}

export type LiveBusyEmployeeResolutionInput = {
  employees: readonly CompanyEmployeeRecord[] | null | undefined;
  /** Thread ids with an active IDE chat stream (including background tabs). */
  streamingThreadIds?: readonly string[] | null;
  threads?: readonly { thread_id: string; employee_id?: string | null }[] | null;
  /** Focused-thread owner when a global stream flag is on (fallback). */
  focusedStreamEmployeeId?: string | null;
};

/**
 * Union of roster mid-shift busy + every streaming thread's owner.
 * Parallel continuous workers must all appear in the Team busy count.
 */
export function resolveLiveBusyEmployeeIds(
  input: LiveBusyEmployeeResolutionInput,
): string[] {
  const ids = new Set<string>();
  for (const row of input.employees ?? []) {
    if (employeeIsActivelyBusy(row)) {
      ids.add(row.employee_id);
    }
  }
  const streaming = new Set(
    (input.streamingThreadIds ?? []).map((id) => id.trim()).filter(Boolean),
  );
  if (streaming.size && input.threads?.length) {
    for (const thread of input.threads) {
      if (!streaming.has(thread.thread_id)) {
        continue;
      }
      const employeeId = thread.employee_id?.trim();
      if (employeeId) {
        ids.add(employeeId);
      }
    }
  }
  const focused = input.focusedStreamEmployeeId?.trim();
  if (focused) {
    ids.add(focused);
  }
  return [...ids];
}
