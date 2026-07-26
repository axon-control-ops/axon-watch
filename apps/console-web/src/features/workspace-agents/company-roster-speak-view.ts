import type { CompanyEmployeeRecord } from '../../contracts/canonical';

import { failureSpeakDetail } from './employee-failure-detail';
import { employeeFailureLine } from './company-roster-failure-view';
import { employeeIsWorking } from './company-roster-status';

export type EmployeeTalkSpeakMode = 'intro' | 'callback';

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
      `${name} again — that last shift still failed on ${failDetail}. Want a retry or a postmortem?`,
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
