import type { CompanyEmployeeRecord } from '../../contracts/canonical';

import {
  OPERATOR_FAILURE_RETRY_LABEL,
  operatorFailureRetryLabel,
} from '../../lib/operator-failure-copy';
import {
  employeeResolvedFailureDetail,
  isAgentSessionInterruptedFailure,
  isMissingConfidenceFailure,
  isOperatorStoppedFailure,
  isRestartInterruptedFailure,
  isRuntimeAuthFailure,
  isCompletionGateFailure,
  isNonRetriableWorkspaceBlockFailure,
  isRuntimeAuthProbeFailure,
  isShiftContinuationFailure,
  isUsageLimitFailure,
  looksLikeSuccessfulOutcomeDetail,
  truncateFailureDetail,
} from './employee-failure-detail';
import { employeeIsWorking, employeeStatusIsActivelyBusy } from './company-roster-status';
import { humanizeEmployeeDeliveryHandoff } from './employee-delivery-handoff-view';

const DOCK_RECEIPT_DETAIL_MAX = 180;

function usageRuntime(detail: string | null | undefined): 'Codex' | 'Claude' | 'Cursor' {
  const normalized = (detail ?? '').toLowerCase();
  if (normalized.includes('codex')) return 'Codex';
  if (normalized.includes('claude')) return 'Claude';
  return 'Cursor';
}

function usageFailureCopy(detail: string | null | undefined): string {
  const runtime = usageRuntime(detail);
  if (runtime === 'Codex' || runtime === 'Claude') {
    return (
      `Last job could not start because the ${runtime} CLI reported a usage-limit block; ` +
      'Axon cannot verify the live account quota. Tap Try again once, or switch runtime.'
    );
  }
  return 'Last job hit a Cursor usage signal — Auto+Composer may still have headroom or on-demand spend. Check Usage in Settings → CLI runtime, then Try again.';
}

function isCorrectOutOfScopeRefusal(detail: string | null | undefined): boolean {
  return /continuous worker scope guard tripped|\bout_of_scope_guard\b/i.test(detail ?? '');
}

export function employeeFailureLine(
  employee: CompanyEmployeeRecord,
  options?: { liveBusy?: boolean },
): string | null {
  const outcome = (employee.last_outcome ?? '').trim().toLowerCase();
  if (outcome !== 'failed') {
    return null;
  }
  // Preserve the failed run receipt, but do not brand a worker failed for
  // correctly refusing work outside its repository or leased scope.
  if (isCorrectOutOfScopeRefusal(employee.last_outcome_detail)) {
    return null;
  }
  // Active jobs / live IDE streams supersede the last failure banner.
  if (options?.liveBusy) {
    return null;
  }
  if (employeeIsWorking(employee.status)) {
    return null;
  }
  // Mid-shift role run — hide stale last-job failures while work is in flight.
  if (
    employee.active_run_id?.trim() &&
    employeeStatusIsActivelyBusy(employee.status)
  ) {
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
      return usageFailureCopy(employee.last_outcome_detail);
    }
    if (isMissingConfidenceFailure(employee.last_outcome_detail)) {
      return 'Last job reply was generated, but acceptance failed because the closing Confidence line was missing. Tap Try again to close it out.';
    }
    if (isRuntimeAuthProbeFailure(employee.last_outcome_detail)) {
      return 'Last job could not run — Cursor CLI auth timed out. Check runtime on the host, then tap Try again.';
    }
    if (isRuntimeAuthFailure(employee.last_outcome_detail)) {
      return 'Last job could not run — login is not ready. Run `cursor agent login` on the host or unlock /vault, then tap Try again.';
    }
    if (isCompletionGateFailure(employee.last_outcome_detail)) {
      return (
        'Last job produced no file changes in the worker isolation checkout — ' +
        'not Composer Sandbox. Tap Try again with a narrower task, or reassign as report-only audit.'
      );
    }
    if (isNonRetriableWorkspaceBlockFailure(employee.last_outcome_detail)) {
      return (
        `Last job blocked (working as intended): ${truncateFailureDetail(detail)} ` +
        'Retrying will fail the same way — an operator must remove or relocate the file first.'
      );
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
  if (isRuntimeAuthProbeFailure(employee.last_outcome_detail)) {
    return 'Cursor CLI auth timed out on the host. Check `cursor agent status`, then retry.';
  }
  if (isRuntimeAuthFailure(employee.last_outcome_detail)) {
    return 'Runtime login is not ready. Run `cursor agent login` or unlock /vault, then retry.';
  }
  if (isUsageLimitFailure(employee.last_outcome_detail)) {
    const runtime = usageRuntime(employee.last_outcome_detail);
    if (runtime === 'Cursor') {
      return 'Cursor usage signal on this shift — Auto+Composer may still have headroom or on-demand spend. Check Usage, then retry.';
    }
    return `Signed-in ${runtime} account quota blocked this shift — switch runtime or enable Auto failover, then retry.`;
  }
  if (isMissingConfidenceFailure(employee.last_outcome_detail)) {
    return 'The agent runtime produced a reply, but Gate 6/Critical Review rejected it because the final line was not `Confidence: N/10`. Retry should only close the report format.';
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

/** Dock receipt body — full technical detail for failures; delivery copy otherwise. */
export function employeeDockReceiptDetail(employee: CompanyEmployeeRecord): string | null {
  const detail = employeeResolvedFailureDetail(employee);
  if (!detail) {
    return null;
  }
  if (employeeFailureLine(employee)) {
    return detail;
  }
  // Prefer plain English when the last outcome is a raw delivery receipt.
  if (/delivery\b|worker\/run_|https?:\/\/|ci[_ ]green|draft.?pr/i.test(detail)) {
    const handoff = humanizeEmployeeDeliveryHandoff({
      stage: employee.pipeline_stage,
      detail: employee.pipeline_detail || detail,
      draftPrUrl: employee.draft_pr_url,
      ciStatus: employee.ci_status,
    });
    if (handoff) {
      return handoff.length <= DOCK_RECEIPT_DETAIL_MAX
        ? handoff
        : `${handoff.slice(0, DOCK_RECEIPT_DETAIL_MAX - 1)}…`;
    }
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

/**
 * True when automated/continuous retry would only burn more Cursor quota.
 * Manual Team "Try again" still stays available — copy warns the operator.
 */
export function employeeFailureBlocksAutoRetry(employee: CompanyEmployeeRecord): boolean {
  return (
    Boolean(employeeFailureLine(employee)) && isUsageLimitFailure(employee.last_outcome_detail)
  );
}

/**
 * True when the last failure is a working-as-intended policy block (e.g. a
 * private-document path never leaves the workspace automatically). Retrying
 * re-runs the same task against the same working tree and fails identically
 * every time, so the "Try again" action must not be offered here.
 */
export function employeeFailureBlocksRetry(employee: CompanyEmployeeRecord): boolean {
  return (
    Boolean(employeeFailureLine(employee)) &&
    isNonRetriableWorkspaceBlockFailure(employee.last_outcome_detail)
  );
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
  liveBusyEmployeeIds?: readonly string[] | null,
): CompanyEmployeeRecord[] {
  const liveBusy = new Set(
    (liveBusyEmployeeIds ?? []).map((id) => id.trim()).filter(Boolean),
  );
  return (employees ?? []).filter((row) =>
    Boolean(
      employeeFailureLine(row, {
        liveBusy: liveBusy.has(row.employee_id),
      }),
    ),
  );
}

export function companyHasFailedEmployees(
  employees: readonly CompanyEmployeeRecord[] | null | undefined,
  liveBusyEmployeeIds?: readonly string[] | null,
): boolean {
  return companyFailedEmployees(employees, liveBusyEmployeeIds).length > 0;
}

export function companyFailedEmployeesHint(
  employees: readonly CompanyEmployeeRecord[] | null | undefined,
  liveBusyEmployeeIds?: readonly string[] | null,
): string | null {
  const failed = companyFailedEmployees(employees, liveBusyEmployeeIds);
  if (!failed.length) {
    return null;
  }
  if (failed.length === 1) {
    const row = failed[0];
    const name = row.name.trim() || 'A teammate';
    const line = employeeFailureLine(row, {
      liveBusy: liveBusyEmployeeIds?.includes(row.employee_id),
    });
    if (line) {
      if (employeeShiftNeedsContinuation(row)) {
        return `${name} — ${line}`;
      }
      // Keep the alert scannable in narrow team rails — full detail stays in title/tooltip.
      const compact = `${name} — last job needs attention. Tap to open dock and Try again.`;
      if (line.length > 96) {
        return compact;
      }
      return `${name} — ${line} Tap to open their dock and Try again.`;
    }
    return `${name}'s last job failed — tap to open their dock and Try again.`;
  }
  return `${failed.length} teammates need attention after a failed job — tap to open a failed teammate's dock and Try again.`;
}

/** Hover title for the roster alert hint when a single teammate failed with truncated detail. */
export function companyFailedEmployeesHintTooltip(
  employees: readonly CompanyEmployeeRecord[] | null | undefined,
  liveBusyEmployeeIds?: readonly string[] | null,
): string | null {
  const failed = companyFailedEmployees(employees, liveBusyEmployeeIds);
  if (failed.length !== 1) {
    return null;
  }
  const row = failed[0];
  const detail = employeeFailureDetailTooltip(row);
  const line = employeeFailureLine(row, {
    liveBusy: liveBusyEmployeeIds?.includes(row.employee_id),
  });
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
  liveBusyEmployeeIds?: readonly string[] | null,
): CompanyRosterAlertBadge | null {
  const needsAttention = companyFailedEmployees(employees, liveBusyEmployeeIds);
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
      title: '1 teammate needs attention — tap to open their dock, then Try again',
      ariaLabel: 'Open failed teammate dock to retry',
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
      title: `${count} teammates need attention — tap to open a failed dock, then Try again`,
      ariaLabel: `Open failed teammate dock to retry (${count})`,
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
