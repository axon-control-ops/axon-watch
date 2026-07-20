import type { CompanyEmployeeRecord } from '../../contracts/canonical';

import {
  employeeResolvedFailureDetail,
  failureSpeakDetail,
  isAgentSessionInterruptedFailure,
  isRestartInterruptedFailure,
  isShiftContinuationFailure,
  isUsageLimitFailure,
  truncateFailureDetail,
} from './employee-failure-detail';

export {
  employeeResolvedFailureDetail,
  failureSpeakDetail,
  isAgentRuntimeFallbackFailure,
  isAgentSessionInterruptedFailure,
  isRestartInterruptedFailure,
  isShiftContinuationFailure,
  isUsageLimitFailure,
  normalizeOperatorFailureDetail,
} from './employee-failure-detail';

const WORKING_STATUSES = new Set([
  'watching',
  'planning',
  'executing',
  'verifying',
  'blocked',
  'waiting_approval',
  'handoff_ready',
]);

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
    return 'last shift failed';
  }
  if (value === 'interrupted') {
    return 'shift interrupted';
  }
  return value.replace(/_/g, ' ');
}

export function employeeIsWorking(status: string | null | undefined): boolean {
  return WORKING_STATUSES.has((status ?? '').trim());
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

export type EmployeeTalkSpeakMode = 'intro' | 'callback';

const DOCK_RECEIPT_DETAIL_MAX = 180;

function stablePickIndex(seed: string, modulo: number): number {
  if (modulo <= 0) {
    return 0;
  }
  let hash = 0;
  for (let i = 0; i < seed.length; i += 1) {
    hash = (hash * 31 + seed.charCodeAt(i)) >>> 0;
  }
  return hash % modulo;
}

function employeeOwnsPhrase(employee: CompanyEmployeeRecord): string {
  return employee.owns?.trim() || employee.role_label?.trim() || 'my lane';
}

function employeeFirstName(employee: CompanyEmployeeRecord): string {
  const name = employee.name.trim() || 'Teammate';
  return name.split(/\s+/)[0] || name;
}

function roleVoiceHook(employee: CompanyEmployeeRecord): string {
  const role = (employee.role ?? '').trim().toLowerCase();
  if (role === 'integrations') {
    return 'connectors and cross-repo wiring';
  }
  if (role === 'frontend') {
    return 'the console UI and dock';
  }
  if (role === 'backend') {
    return 'APIs, runs, and persistence';
  }
  if (role === 'watcher') {
    return 'signals and runtime health';
  }
  if (role === 'lead' || employee.primary) {
    return 'the company briefing and priorities';
  }
  return employeeOwnsPhrase(employee);
}

function statusBeat(employee: CompanyEmployeeRecord): string {
  const owns = employeeOwnsPhrase(employee);
  const status = (employee.status ?? '').trim();
  if (status === 'watching') {
    return `I'm on watch over ${owns}`;
  }
  if (status === 'planning') {
    return `I'm planning the next cut on ${owns}`;
  }
  if (status === 'executing') {
    return `I'm in the middle of ${owns}`;
  }
  if (status === 'verifying') {
    return `I'm verifying ${owns} before handoff`;
  }
  if (status === 'blocked') {
    return `I'm blocked on ${owns} and need a decision`;
  }
  if (status === 'waiting_approval') {
    return `I'm waiting on approval for ${owns}`;
  }
  if (status === 'handoff_ready') {
    return `${owns} is ready to hand off`;
  }
  if (!employee.enabled) {
    return `I'm paused on ${owns}`;
  }
  return `I'm idle on ${owns}`;
}

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
      return 'Last shift interrupted by server restart — use Retry shift to continue.';
    }
    if (isAgentSessionInterruptedFailure(detail)) {
      return 'Last shift interrupted before it could finish — use Retry shift to continue.';
    }
    if (isUsageLimitFailure(employee.last_outcome_detail)) {
      return 'Last shift could not start — usage limits blocked the agent runtime. Restore limits, then use Retry shift.';
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

/** Surface failed teammates first, then live workers, then lead/primary, then name. */
export function sortEmployeesForPresenceStrip(
  employees: readonly CompanyEmployeeRecord[],
): CompanyEmployeeRecord[] {
  const rank = (employee: CompanyEmployeeRecord): number[] => {
    const failed = employeeFailureLine(employee) ? 0 : 1;
    const working = employeeIsWorking(employee.status) ? 0 : 1;
    const lead = employee.primary || (employee.role ?? '').trim().toLowerCase() === 'lead' ? 0 : 1;
    return [failed, working, lead];
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

/** Default dock selection: failed first, then primary/lead, then first row. */
export function pickDefaultRosterEmployee(
  employees: readonly CompanyEmployeeRecord[],
): CompanyEmployeeRecord | null {
  if (!employees.length) {
    return null;
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

/** Restart or SIGTERM — retry should continue rather than treat as a hard failure. */
export function employeeShiftNeedsContinuation(employee: CompanyEmployeeRecord): boolean {
  if (!employeeFailureLine(employee)) {
    return false;
  }
  return isShiftContinuationFailure(employee.last_outcome_detail);
}

/** Status chip value: surfaces failed when the last shift failed and the teammate is idle. */
export function employeeDisplayStatus(employee: CompanyEmployeeRecord): string {
  if (employeeFailureLine(employee)) {
    return employeeShiftNeedsContinuation(employee) ? 'interrupted' : 'failed';
  }
  const status = (employee.status ?? '').trim();
  return status || 'idle';
}

export function employeeTalkLine(employee: CompanyEmployeeRecord): string | null {
  const failure = employeeFailureLine(employee);
  if (failure) {
    return failure;
  }
  if (!employeeIsWorking(employee.status)) {
    return null;
  }
  const owns = employeeOwnsPhrase(employee);
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

function employeeStatusSpeakLine(employee: CompanyEmployeeRecord): string {
  const name = employeeFirstName(employee);
  const hook = roleVoiceHook(employee);
  const beat = statusBeat(employee);
  const failDetail = employeeFailureLine(employee) ? failureSpeakDetail(employee) : null;

  if (failDetail) {
    return (
      `${name} reporting in. ${beat}. Last shift failed on: ${failDetail}. ` +
      `I can retry that shift, or walk the receipts with you — your call.`
    );
  }
  if (employeeIsWorking(employee.status)) {
    return (
      `${name} reporting in. ${beat}. My focus is ${hook}. ` +
      `Ask me for blockers, or tell me what to prioritize next.`
    );
  }
  if (!employee.enabled) {
    return (
      `${name} here — paused. I still own ${hook}, but I won't take continuous shifts until you enable me again.`
    );
  }
  return (
    `${name} reporting in. ${beat}. Quiet for now on ${hook}. ` +
    `Ask me a question, assign work, or send me on a shift.`
  );
}

function employeeIntroSpeakLine(employee: CompanyEmployeeRecord): string {
  const name = employeeFirstName(employee);
  const hook = roleVoiceHook(employee);
  const beat = statusBeat(employee);
  const failDetail = employeeFailureLine(employee) ? failureSpeakDetail(employee) : null;

  if (failDetail) {
    return (
      `Hey — ${name}. I own ${hook}. ${beat}, and the last shift failed: ${failDetail}. ` +
      `Hit Retry shift when you want another go, or talk me through what broke.`
    );
  }
  if (employeeIsWorking(employee.status)) {
    return (
      `Hey — ${name}. I own ${hook}. ${beat}. ` +
      `I'm live if you need a status, a redirect, or a handoff.`
    );
  }
  if (!employee.enabled) {
    return (
      `Hey — ${name}. I own ${hook}, but I'm paused from continuous shifts. ` +
      `Enable me when you want me back on the roster.`
    );
  }
  return (
    `Hey — ${name}. I own ${hook}. ${beat}. ` +
    `What do you need from me?`
  );
}

function employeeCallbackSpeakLine(
  employee: CompanyEmployeeRecord,
  entropy = '',
): string {
  const name = employeeFirstName(employee);
  const owns = employeeOwnsPhrase(employee);
  const hook = roleVoiceHook(employee);
  const seed = `${employee.employee_id}:${employee.status}:${entropy}`;
  const failDetail = employeeFailureLine(employee) ? failureSpeakDetail(employee) : null;

  if (failDetail) {
    const failedLines = [
      `${name} again — that last shift still failed on ${failDetail}. Retry, or dig in with me?`,
      `Yeah, it's ${name}. Failure still stands: ${failDetail}. Want a retry or a postmortem?`,
      `${name} here. ${owns} is quiet after a failed shift — ${failDetail}. Your move.`,
    ] as const;
    return failedLines[stablePickIndex(seed, failedLines.length)];
  }

  if (employeeIsWorking(employee.status)) {
    const workingLines = [
      `${name} — still mid-${owns}. What's up?`,
      `${name} here. ${statusBeat(employee)}. Talk to me if you need a pivot.`,
      `You caught ${name} live on ${hook}. Need a status or a change of plan?`,
      `${name} listening — ${owns} is in flight. Go ahead.`,
    ] as const;
    return workingLines[stablePickIndex(seed, workingLines.length)];
  }

  if (!employee.enabled) {
    return `${name} here — still paused. Enable me when you want continuous work again.`;
  }

  const idleLines = [
    `${name} here. What's on your mind for ${hook}?`,
    `${name} — you called. I'm free on ${owns}; assign me or ask.`,
    `Yeah, ${name}. Quiet on ${hook} right now — what do you need?`,
    `${name} checking in. Ready when you are.`,
  ] as const;
  return idleLines[stablePickIndex(seed, idleLines.length)];
}

export function employeeSpeakLine(
  employee: CompanyEmployeeRecord,
  kind: 'talk' | 'status' = 'talk',
  options: { talkMode?: EmployeeTalkSpeakMode; entropy?: string } = {},
): string {
  if (kind === 'status') {
    return employeeStatusSpeakLine(employee);
  }

  const talkMode = options.talkMode ?? 'intro';
  if (talkMode === 'callback') {
    return employeeCallbackSpeakLine(employee, options.entropy ?? '');
  }
  return employeeIntroSpeakLine(employee);
}

export function employeeMetaLine(employee: CompanyEmployeeRecord): string {
  // Role is shown as a badge next to the name — meta is schedule only.
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
