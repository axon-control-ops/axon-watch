import type { CompanyEmployeeRecord } from '../../contracts/canonical';

import {
  OPERATOR_FAILURE_RETRY_LABEL,
  operatorFailureRetryLabel,
} from '../../lib/operator-failure-copy';
import {
  employeeResolvedFailureDetail,
  isAgentSessionInterruptedFailure,
  isOperatorStoppedFailure,
  isRestartInterruptedFailure,
  isRuntimeAuthFailure,
  isShiftContinuationFailure,
  isUsageLimitFailure,
  looksLikeSuccessfulOutcomeDetail,
  truncateFailureDetail,
} from './employee-failure-detail';
import { employeeIsWorking } from './company-roster-status';

const DOCK_RECEIPT_DETAIL_MAX = 180;

export function employeeFailureLine(employee: CompanyEmployeeRecord): string | null {
  const outcome = (employee.last_outcome ?? '').trim().toLowerCase();
  if (outcome !== 'failed') {
    return null;
  }
  // Active jobs supersede the last failure banner.
  if (employeeIsWorking(employee.status)) {
    return null;
  }
  const detail = employeeResolvedFailureDetail(employee);
  // Stale failed tags with a success detail must not keep the red banner up.
  if (looksLikeSuccessfulOutcomeDetail(detail)) {
    return null;
  }
  if (detail) {
    if (isRestartInterruptedFailure(detail)) {
      return 'Last job was interrupted when the server restarted — tap Continue to pick up where they left off.';
    }
    if (isOperatorStoppedFailure(detail)) {
      return 'Last job was stopped early — tap Continue to pick up where they left off.';
    }
    if (isAgentSessionInterruptedFailure(detail)) {
      if (
        /\boom[- ]?kill/i.test(detail) ||
        /exited with status 137/i.test(detail) ||
        /exited with status -?9\b/i.test(detail)
      ) {
        return 'Last job was stopped to free memory — tap Continue when the machine has headroom.';
      }
      return 'Last job was interrupted before it could finish — tap Continue to pick up where they left off.';
    }
    if (isUsageLimitFailure(employee.last_outcome_detail)) {
      return 'Last job could not start — usage limits blocked the agent. Restore limits, then tap Try again.';
    }
    if (isRuntimeAuthFailure(employee.last_outcome_detail)) {
      return 'Last job could not run — login is not ready. Run `cursor agent login` on the host or unlock /vault, then tap Try again.';
    }
    return `Last job failed: ${truncateFailureDetail(detail)}`;
  }
  return 'Last job failed — open the run for details.';
}

/** Stable dedupe key for auto-peeking the agent dock after a failed job. */
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

/** Primary recovery action label for failed or interrupted teammate jobs. */
export function employeeFailureRetryActionLabel(employee: CompanyEmployeeRecord): string {
  if (!employeeFailureLine(employee)) {
    return OPERATOR_FAILURE_RETRY_LABEL;
  }
  return operatorFailureRetryLabel(employeeShiftNeedsContinuation(employee));
}

/** Status chip value: surfaces failed when the last job failed and the teammate is idle. */
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
    return `${name}'s last job failed — select them and tap Try again, or click to talk it through.`;
  }
  return `${failed.length} teammates need attention after a failed job — select one and tap Try again, or click to talk it through.`;
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

/** Compact roster headline badge when teammates need attention after a failed or interrupted job. */
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
        title: '1 teammate has an interrupted job — select them and tap Continue',
        ariaLabel: 'Jump to 1 interrupted teammate',
        tone: 'interrupted',
      };
    }

    return {
      label: '1 failed',
      title: '1 teammate needs attention after a failed job',
      ariaLabel: 'Jump to 1 failed teammate',
      tone: 'failure',
    };
  }

  if (failedCount === 0) {
    return {
      label: `${count} interrupted`,
      title: `${count} teammates have interrupted jobs — select one and tap Continue`,
      ariaLabel: `Jump to ${count} interrupted teammates`,
      tone: 'interrupted',
    };
  }

  if (interruptedCount === 0) {
    return {
      label: `${count} failed`,
      title: `${count} teammates need attention after a failed job`,
      ariaLabel: `Jump to ${count} failed teammates`,
      tone: 'failure',
    };
  }

  return {
    label: `${count} need attention`,
    title: `${count} teammates need attention after a failed or interrupted job`,
    ariaLabel: `Jump to ${count} teammates needing attention`,
    tone: 'mixed',
  };
}
