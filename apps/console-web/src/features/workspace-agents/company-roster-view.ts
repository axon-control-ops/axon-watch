import type { CompanyEmployeeRecord } from '../../contracts/canonical';
import { OPERATOR_FAILURE_STATUS_LABEL } from '../../lib/operator-failure-copy';

import { employeeFailureDetailTooltip, employeeFailureLine } from './company-roster-failure-view';
import { employeeIsWorking } from './company-roster-status';

export {
  employeeTalkLine,
  employeeTalkLineDetailTooltip,
} from './company-roster-talk-view';

export {
  employeeResolvedFailureDetail,
  failureSpeakDetail,
  isAgentRuntimeFallbackFailure,
  isAgentSessionInterruptedFailure,
  isMissingConfidenceFailure,
  isCompletionGateFailure,
  isOperatorStoppedFailure,
  isRestartInterruptedFailure,
  isShiftContinuationFailure,
  isRuntimeAuthFailure,
  isRuntimeAuthProbeFailure,
  isUsageLimitFailure,
  looksLikeSuccessfulOutcomeDetail,
  normalizeOperatorFailureDetail,
} from './employee-failure-detail';

export { employeeIsWorking, employeeStatusIsActivelyBusy } from './company-roster-status';
export {
  companyBusyEmployees,
  companyBusyEmployeesCount,
  employeeIsActivelyBusy,
  employeeIsLeadLikeRole,
  resolveLiveBusyEmployeeIds,
  resolveReportingEmployeeId,
} from './company-roster-busy';
export {
  employeeSpeakLine,
  type EmployeeTalkSpeakMode,
} from './company-roster-speak-view';

export { employeeRuntimeShiftHint } from './employee-runtime-shift-view';

export {
  buildCompanyRosterAlertBadge,
  companyFailedEmployees,
  companyFailedEmployeesHint,
  companyFailedEmployeesHintTooltip,
  companyHasFailedEmployees,
  employeeDisplayStatus,
  employeeFailureBannerAriaLabel,
  employeeFailureBannerCopy,
  employeeFailureBeatAriaLabel,
  employeeFailureDetailTooltip,
  employeeFailureLine,
  employeeFailurePeekKey,
  employeeFailureRetryActionLabel,
  employeeFailureBlocksAutoRetry,
  employeeFailureBlocksRetry,
  employeeShiftNeedsContinuation,
  employeeDockReceiptDetail,
  type CompanyRosterAlertBadge,
  type CompanyRosterAlertBadgeTone,
} from './company-roster-failure-view';

export type EmployeeGlowTone =
  | 'lead'
  | 'watcher'
  | 'frontend'
  | 'backend'
  | 'integrations'
  | 'default';

export function employeeStatusLabel(status: string | null | undefined): string {
  const value = (status ?? '').trim();
  if (!value) {
    return 'idle';
  }
  if (value === 'failed') {
    return OPERATOR_FAILURE_STATUS_LABEL;
  }
  if (value === 'interrupted') {
    return 'job interrupted';
  }
  return value.replace(/_/g, ' ');
}

export function employeeGlowTone(employee: CompanyEmployeeRecord): EmployeeGlowTone {
  const role = (employee.role ?? '').trim().toLowerCase();
  if (role === 'lead' || employee.primary) {
    return 'lead';
  }
  if (role === 'watcher') {
    return 'watcher';
  }
  if (role === 'frontend') {
    return 'frontend';
  }
  if (role === 'backend') {
    return 'backend';
  }
  if (role === 'integrations') {
    return 'integrations';
  }
  return 'default';
}

export function employeeDockReceiptRunId(employee: CompanyEmployeeRecord): string | null {
  return (
    employee.active_run_id?.trim() ||
    employee.last_run_id?.trim() ||
    null
  );
}

/** Short run id for dock receipts — full id stays in title for copy/debug. */
export function employeeDockReceiptRunLabel(runId: string | null | undefined): string | null {
  const value = (runId ?? '').trim();
  if (!value) {
    return null;
  }
  const short = value.startsWith('run_') ? value.slice(4, 10) : value.slice(0, 6);
  return short ? `#${short}` : null;
}

export type PresenceStripMove = 'prev' | 'next' | 'first' | 'last';

/** Keyboard step through the sorted presence strip (wraps at ends). */
export function adjacentPresenceStripEmployee(
  employees: readonly CompanyEmployeeRecord[],
  currentId: string | null | undefined,
  move: PresenceStripMove,
): CompanyEmployeeRecord | null {
  const sorted = sortEmployeesForPresenceStrip(employees);
  if (!sorted.length) {
    return null;
  }
  if (move === 'first') {
    return sorted[0];
  }
  if (move === 'last') {
    return sorted[sorted.length - 1];
  }
  const index = sorted.findIndex((row) => row.employee_id === (currentId ?? '').trim());
  if (index < 0) {
    return move === 'prev' ? sorted[sorted.length - 1] : sorted[0];
  }
  const delta = move === 'prev' ? -1 : 1;
  const nextIndex = (index + delta + sorted.length) % sorted.length;
  return sorted[nextIndex];
}

/** First teammate with a pending VAXON decision. */
export function firstPendingDecisionEmployee(
  employees: readonly CompanyEmployeeRecord[],
): CompanyEmployeeRecord | null {
  return employees.find((row) => Boolean(row.pending_decision_id?.trim())) ?? null;
}

/** Surface failed teammates first, then live workers, then lead/primary, then name. */
export function sortEmployeesForPresenceStrip(
  employees: readonly CompanyEmployeeRecord[],
): CompanyEmployeeRecord[] {
  const rank = (employee: CompanyEmployeeRecord): number[] => {
    const pending = employee.pending_decision_id?.trim() ? 0 : 1;
    const failed = employeeFailureLine(employee) ? 0 : 1;
    const working = employeeIsWorking(employee.status) ? 0 : 1;
    const lead = employee.primary || (employee.role ?? '').trim().toLowerCase() === 'lead' ? 0 : 1;
    return [pending, failed, working, lead];
  };

  return [...employees].sort((left, right) => {
    const leftRank = rank(left);
    const rightRank = rank(right);
    for (let index = 0; index < leftRank.length; index += 1) {
      if (leftRank[index] !== rightRank[index]) {
        return leftRank[index] - rightRank[index];
      }
    }
    return left.name.localeCompare(right.name, undefined, { sensitivity: 'base' });
  });
}

/** First failed teammate in presence-strip order (failed → working → lead → name). */
export function firstFailedRosterEmployee(
  employees: readonly CompanyEmployeeRecord[],
): CompanyEmployeeRecord | null {
  return sortEmployeesForPresenceStrip(employees).find((row) => employeeFailureLine(row)) ?? null;
}

/** Default dock selection: pending decision first, then failed, then primary/lead. */
export function pickDefaultRosterEmployee(
  employees: readonly CompanyEmployeeRecord[],
): CompanyEmployeeRecord | null {
  if (!employees.length) {
    return null;
  }
  const pending = firstPendingDecisionEmployee(employees);
  if (pending) {
    return pending;
  }
  const failed = firstFailedRosterEmployee(employees);
  if (failed) {
    return failed;
  }
  const primary =
    employees.find((row) => row.primary) ?? employees.find((row) => row.role === 'lead');
  return primary ?? employees[0];
}

/** Stable id for the persona dock panel — pairs with presence strip aria-controls. */
export const COMPANY_ROSTER_DOCK_ID = 'company-roster-agent-dock';

export function presenceStripOptionId(employeeId: string | null | undefined): string {
  const value = (employeeId ?? '').trim();
  return value ? `company-presence-option-${value}` : '';
}

/** Failure, pause, or live shift context for presence strip labels and titles. */
export function employeePresenceContextPhrase(employee: CompanyEmployeeRecord): string | null {
  const failure = employeeFailureLine(employee);
  if (failure) {
    return failure;
  }
  if (!employee.enabled) {
    return 'Paused';
  }
  if (employeeIsWorking(employee.status)) {
    return employeeStatusLabel(employee.status);
  }
  return null;
}

export function employeePresenceSelectLabel(employee: CompanyEmployeeRecord): string {
  const name = employee.name.trim() || 'teammate';
  const context = employeePresenceContextPhrase(employee);
  if (context) {
    const phrase = context === 'Paused' ? 'paused' : context;
    return `Select ${name}, ${phrase}`;
  }
  return `Select ${name}`;
}

/** Hover title for presence strip avatars — name plus failure or pause context. */
export function employeePresenceStripTitle(employee: CompanyEmployeeRecord): string {
  const name = employee.name.trim() || 'Teammate';
  const context = employeePresenceContextPhrase(employee);
  if (context) {
    return `${name} — ${context}`;
  }
  return name;
}

/** Presence strip hover title — prefers full failure detail when the compact line truncates. */
export function employeePresenceStripHoverTitle(employee: CompanyEmployeeRecord): string {
  const detail = employeeFailureDetailTooltip(employee);
  const failure = employeeFailureLine(employee);
  if (detail && failure && (failure.endsWith('…') || !failure.includes(detail))) {
    return detail;
  }
  return employeePresenceStripTitle(employee);
}

/** Screen reader label for presence strip options — adds full failure detail when truncated. */
export function employeePresenceSelectAriaLabel(employee: CompanyEmployeeRecord): string {
  const base = employeePresenceSelectLabel(employee);
  const detail = employeeFailureDetailTooltip(employee);
  const failure = employeeFailureLine(employee);
  if (!detail || !failure) {
    return base;
  }
  if (failure.endsWith('…') || !failure.includes(detail)) {
    return `${base}. Full detail: ${detail}`;
  }
  return base;
}

/** Currently highlighted teammate in the presence strip (for keyboard confirm). */
export function selectedPresenceStripEmployee(
  employees: readonly CompanyEmployeeRecord[],
  selectedId: string | null | undefined,
): CompanyEmployeeRecord | null {
  const id = (selectedId ?? '').trim();
  if (!id) {
    return null;
  }
  return employees.find((row) => row.employee_id === id) ?? null;
}

export function employeeMetaLine(employee: CompanyEmployeeRecord): string {
  return (employee.schedule_label?.trim() || employee.schedule || '').trim();
}

export function employeeRoleBadge(employee: CompanyEmployeeRecord): string {
  return (employee.role_label?.trim() || employee.role || 'Agent').trim();
}

export function companyHeadline(
  companyName: string | null | undefined,
  employeeCount: number | null | undefined,
): string {
  const name = (companyName ?? '').trim() || 'Company';
  const count = typeof employeeCount === 'number' ? employeeCount : 0;
  if (count <= 0) {
    return name;
  }
  return `${name} · ${count} employee${count === 1 ? '' : 's'}`;
}

export function companyHasWorkingEmployees(
  employees: readonly CompanyEmployeeRecord[] | null | undefined,
): boolean {
  return (employees ?? []).some((row) => employeeIsWorking(row.status));
}
