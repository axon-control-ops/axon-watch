import type { CompanyEmployeeRecord } from '../../contracts/canonical';

import {
  employeeResolvedFailureDetail,
  isAgentSessionInterruptedFailure,
  isOperatorStoppedFailure,
  isRestartInterruptedFailure,
  isRuntimeAuthFailure,
  isShiftContinuationFailure,
  isUsageLimitFailure,
  truncateFailureDetail,
} from './employee-failure-detail';
import { employeeIsWorking } from './company-roster-status';

const DOCK_RECEIPT_DETAIL_MAX = 180;

export function employeeFailureLine(employee: CompanyEmployeeRecord): string | null {
  const outcome = (employee.last_outcome ?? '').trim().toLowerCase();
  if (outcome !== 'failed') {
    return null;
  }
  // Active shifts supersede the last failure banner.
  if (employeeIsWorking(employee.status)) {
    return null;
  }
  const detail = employeeResolvedFailureDetail(employee);
  if (detail) {
    if (isRestartInterruptedFailure(detail)) {
      return 'Last shift interrupted by server restart — use Continue shift to pick up where you left off.';
    }
    if (isOperatorStoppedFailure(detail)) {
      return 'Last shift was stopped early — use Continue shift to pick up where you left off.';
    }
    if (isAgentSessionInterruptedFailure(detail)) {
      if (
        /\boom[- ]?kill/i.test(detail) ||
        /exited with status 137/i.test(detail) ||
        /exited with status -?9\b/i.test(detail)
      ) {
        return 'Last shift was stopped to free memory — use Continue shift when the machine has headroom.';
      }
      return 'Last shift interrupted before it could finish — use Continue shift to pick up where you left off.';
    }
    if (isUsageLimitFailure(employee.last_outcome_detail)) {
      return 'Last shift could not start — usage limits blocked the agent runtime. Restore limits, then use Retry shift.';
    }
    if (isRuntimeAuthFailure(employee.last_outcome_detail)) {
      return 'Last shift could not run — runtime auth is not ready. Run `cursor agent login` on the host or unlock /vault, then use Retry shift.';
    }
    return `Last shift failed: ${truncateFailureDetail(detail)}`;
  }
  return 'Last shift failed — open the run for receipts.';
}

/** Stable dedupe key for auto-peeking the agent dock after a failed shift. */
export function employeeFailurePeekKey(employee: CompanyEmployeeRecord): string | null {
  if (!employeeFailureLine(employee)) {
    return null;
  }
  const runId = employee.last_run_id?.trim();
  if (runId) {
    return `${employee.employee_id}:${runId}`;
  }
  const detail = employeeResolvedFailureDetail(employee);
  if (detail) {
    return `${employee.employee_id}:${detail}`;
  }
  return `${employee.employee_id}:failed`;
}

/** Full last-shift detail for title/tooltip when the compact failure line is truncated. */
export function employeeFailureDetailTooltip(
  employee: CompanyEmployeeRecord,
): string | undefined {
  if (!employeeFailureLine(employee)) {
    return undefined;
  }
  const detail = employeeResolvedFailureDetail(employee);
  return detail || undefined;
}

/** Composer dock banner — prefix teammate name when the failure line stands alone. */
export function employeeFailureBannerCopy(employee: CompanyEmployeeRecord): string {
  const line = employeeFailureLine(employee);
  if (!line) {
    return '';
  }
  const name = employee.name?.trim();
  if (!name) {
    return line;
  }
  return `${name} — ${line}`;
}

/** Screen-reader label for the composer failure banner — includes full detail when truncated. */
export function employeeFailureBannerAriaLabel(
  employee: CompanyEmployeeRecord,
): string | undefined {
  const copy = employeeFailureBannerCopy(employee);
  if (!copy) {
    return undefined;
  }
  return employeeFailureStatusAriaLabel(copy, employee);
}

/** Screen-reader label for persona dock / roster failure beats — full detail when truncated. */
export function employeeFailureBeatAriaLabel(
  employee: CompanyEmployeeRecord,
): string | undefined {
  const line = employeeFailureLine(employee);
  if (!line) {
    return undefined;
  }
  return employeeFailureStatusAriaLabel(line, employee);
}

function employeeFailureStatusAriaLabel(
  spokenLine: string,
  employee: CompanyEmployeeRecord,
): string {
  const detail = employeeFailureDetailTooltip(employee);
  const line = employeeFailureLine(employee);
  if (!detail || !line) {
    return spokenLine;
  }
  if (line.endsWith('…') || !line.includes(detail)) {
    return `${spokenLine}. Full detail: ${detail}`;
  }
  return spokenLine;
}

/** Dock receipt body — skip when the failure beat already carries outcome detail. */
export function employeeDockReceiptDetail(employee: CompanyEmployeeRecord): string | null {
  const detail = employeeResolvedFailureDetail(employee);
  if (!detail || employeeFailureLine(employee)) {
    return null;
  }
  if (detail.length <= DOCK_RECEIPT_DETAIL_MAX) {
    return detail;
  }
  return `${detail.slice(0, DOCK_RECEIPT_DETAIL_MAX - 1)}…`;
}

/** Restart or SIGTERM — retry should continue rather than treat as a hard failure. */
export function employeeShiftNeedsContinuation(employee: CompanyEmployeeRecord): boolean {
  if (!employeeFailureLine(employee)) {
    return false;
  }
  return isShiftContinuationFailure(employee.last_outcome_detail);
}

/** Primary recovery action label for failed or interrupted teammate shifts. */
export function employeeFailureRetryActionLabel(employee: CompanyEmployeeRecord): string {
  if (!employeeFailureLine(employee)) {
    return 'Retry shift';
  }
  return employeeShiftNeedsContinuation(employee) ? 'Continue shift' : 'Retry shift';
}

/** Status chip value: surfaces failed when the last shift failed and the teammate is idle. */
export function employeeDisplayStatus(employee: CompanyEmployeeRecord): string {
  if (employeeFailureLine(employee)) {
    return employeeShiftNeedsContinuation(employee) ? 'interrupted' : 'failed';
  }
  const status = (employee.status ?? '').trim();
  return status || 'idle';
}

export function companyFailedEmployees(
  employees: readonly CompanyEmployeeRecord[] | null | undefined,
): CompanyEmployeeRecord[] {
  return (employees ?? []).filter((row) => Boolean(employeeFailureLine(row)));
}

export function companyHasFailedEmployees(
  employees: readonly CompanyEmployeeRecord[] | null | undefined,
): boolean {
  return companyFailedEmployees(employees).length > 0;
}

export function companyFailedEmployeesHint(
  employees: readonly CompanyEmployeeRecord[] | null | undefined,
): string | null {
  const failed = companyFailedEmployees(employees);
  if (!failed.length) {
    return null;
  }
  if (failed.length === 1) {
    const row = failed[0];
    const name = row.name.trim() || 'A teammate';
    const line = employeeFailureLine(row);
    if (line) {
      return `${name} — ${line}`;
    }
    return `${name}'s last shift failed — select them for Retry shift, or click to talk it through.`;
  }
  return `${failed.length} teammates need attention after a failed shift — select one for Retry shift, or click to talk it through.`;
}

/** Hover title for the roster alert hint when a single teammate failed with truncated detail. */
export function companyFailedEmployeesHintTooltip(
  employees: readonly CompanyEmployeeRecord[] | null | undefined,
): string | null {
  const failed = companyFailedEmployees(employees);
  if (failed.length !== 1) {
    return null;
  }
  const row = failed[0];
  const detail = employeeFailureDetailTooltip(row);
  const line = employeeFailureLine(row);
  if (!detail || !line || (!line.endsWith('…') && line.includes(detail))) {
    return null;
  }
  const name = row.name.trim() || 'A teammate';
  return `${name} — ${detail}`;
}

export type CompanyRosterAlertBadgeTone = 'failure' | 'interrupted' | 'mixed';

export type CompanyRosterAlertBadge = {
  label: string;
  title: string;
  ariaLabel: string;
  tone: CompanyRosterAlertBadgeTone;
};

/** Compact roster headline badge when teammates need attention after a failed or interrupted shift. */
export function buildCompanyRosterAlertBadge(
  employees: readonly CompanyEmployeeRecord[] | null | undefined,
): CompanyRosterAlertBadge | null {
  const needsAttention = companyFailedEmployees(employees);
  const count = needsAttention.length;
  if (count === 0) {
    return null;
  }

  const interruptedCount = needsAttention.filter((row) =>
    employeeShiftNeedsContinuation(row),
  ).length;
  const failedCount = count - interruptedCount;

  if (count === 1) {
    if (interruptedCount === 1) {
      return {
        label: '1 interrupted',
        title: '1 teammate has an interrupted shift — select them for Continue shift',
        ariaLabel: 'Jump to 1 interrupted teammate',
        tone: 'interrupted',
      };
    }

    return {
      label: '1 failed',
      title: '1 teammate needs attention after a failed shift',
      ariaLabel: 'Jump to 1 failed teammate',
      tone: 'failure',
    };
  }

  if (failedCount === 0) {
    return {
      label: `${count} interrupted`,
      title: `${count} teammates have interrupted shifts — select one for Continue shift`,
      ariaLabel: `Jump to ${count} interrupted teammates`,
      tone: 'interrupted',
    };
  }

  if (interruptedCount === 0) {
    return {
      label: `${count} failed`,
      title: `${count} teammates need attention after a failed shift`,
      ariaLabel: `Jump to ${count} failed teammates`,
      tone: 'failure',
    };
  }

  return {
    label: `${count} need attention`,
    title: `${count} teammates need attention after a failed or interrupted shift`,
    ariaLabel: `Jump to ${count} teammates needing attention`,
    tone: 'mixed',
  };
}
