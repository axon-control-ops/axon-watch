import type { CompanyEmployeeRecord } from '../../contracts/canonical';

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

const IDLE_CALLBACK_LINES = [
  'Yes?',
  'You called?',
  'Need something?',
  "I'm here.",
  'Go ahead.',
  'Right here — what do you need?',
  'Present.',
  'On deck.',
] as const;

const WORKING_CALLBACK_LINES = [
  (owns: string) => `Yep — still on ${owns}.`,
  (owns: string) => `You need me? Mid-${owns}.`,
  (owns: string) => `Here — ${owns} is in progress.`,
  (owns: string) => `Listening — wrapping ${owns}.`,
  (owns: string) => `Yes boss — ${owns} first, then you.`,
  (owns: string) => `On it already — ${owns}. What's up?`,
] as const;

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

export function employeeTalkLine(employee: CompanyEmployeeRecord): string | null {
  if (!employeeIsWorking(employee.status)) {
    return null;
  }
  const owns = employee.owns?.trim() || employee.role_label?.trim() || 'assigned work';
  const status = (employee.status ?? '').trim();
  if (status === 'watching') {
    return `Still watching ${owns}.`;
  }
  if (status === 'planning') {
    return `Planning next steps on ${owns}.`;
  }
  if (status === 'executing') {
    return `Working on ${owns} right now.`;
  }
  if (status === 'verifying') {
    return `Checking ${owns} before handoff.`;
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

function employeeIntroSpeakLine(employee: CompanyEmployeeRecord): string {
  const name = employee.name.trim() || 'Teammate';
  const owns = employee.owns?.trim() || employee.role_label?.trim() || 'assigned work';
  const working = employeeTalkLine(employee);
  if (working) {
    return `${name} here. ${working}`;
  }
  return `${name} here. Ready to help with ${owns}.`;
}

function employeeCallbackSpeakLine(
  employee: CompanyEmployeeRecord,
  entropy = '',
): string {
  const owns = employee.owns?.trim() || employee.role_label?.trim() || 'assigned work';
  const seed = `${employee.employee_id}:${employee.status}:${entropy}`;
  if (employeeIsWorking(employee.status)) {
    const idx = stablePickIndex(seed, WORKING_CALLBACK_LINES.length);
    return WORKING_CALLBACK_LINES[idx](owns);
  }
  const idx = stablePickIndex(seed, IDLE_CALLBACK_LINES.length);
  return IDLE_CALLBACK_LINES[idx];
}

export function employeeSpeakLine(
  employee: CompanyEmployeeRecord,
  kind: 'talk' | 'status' = 'talk',
  options: { talkMode?: EmployeeTalkSpeakMode; entropy?: string } = {},
): string {
  const name = employee.name.trim() || 'Teammate';
  const owns = employee.owns?.trim() || employee.role_label?.trim() || 'assigned work';
  if (kind === 'status') {
    const working = employeeTalkLine(employee);
    if (working) {
      return working;
    }
    return `${name} here — currently idle on ${owns}.`;
  }

  const talkMode = options.talkMode ?? 'intro';
  if (talkMode === 'callback') {
    return employeeCallbackSpeakLine(employee, options.entropy ?? '');
  }
  return employeeIntroSpeakLine(employee);
}

export function employeeMetaLine(employee: CompanyEmployeeRecord): string {
  const role = employee.role_label?.trim() || employee.role;
  const schedule = employee.schedule_label?.trim() || employee.schedule;
  return `${role} · ${schedule}`;
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
