import type { CompanyEmployeeRecord } from '../../contracts/canonical';

import {
  employeeFailureLine,
  employeeGlowTone,
  employeeIsActivelyBusy,
  employeeIsWorking,
  employeeShiftNeedsContinuation,
  type EmployeeGlowTone,
} from './company-roster-view';
import { buildEmployeeFaceAvatarUrl } from './employee-face-avatar';

export type EmployeePresenceTone =
  | 'idle'
  | 'working'
  | 'handoff'
  | 'approval'
  | 'failed'
  | 'interrupted'
  | 'paused';

export type EmployeeAvatarModel = {
  initials: string;
  background: string;
  foreground: string;
  glow: EmployeeGlowTone;
  presence: EmployeePresenceTone;
  /** Lead / primary operator of the company roster. */
  lead: boolean;
  /** Monday-style illustrated face (SVG data URL). */
  faceUrl: string;
};

/** Role-tinted palette — stable, no external images. */
const ROLE_PALETTE: Record<
  EmployeeGlowTone,
  { background: string; foreground: string }
> = {
  lead: { background: '#2a4a7a', foreground: '#d8e8ff' },
  watcher: { background: '#1a5a42', foreground: '#c8ffe8' },
  frontend: { background: '#1f4f6e', foreground: '#c8ecff' },
  backend: { background: '#3d2f6e', foreground: '#e0d6ff' },
  integrations: { background: '#6a4520', foreground: '#ffe2b8' },
  default: { background: '#2f3d4d', foreground: '#d0e0f0' },
};

function hashSeed(seed: string): number {
  let hash = 2166136261;
  for (let i = 0; i < seed.length; i += 1) {
    hash ^= seed.charCodeAt(i);
    hash = Math.imul(hash, 16777619);
  }
  return hash >>> 0;
}

/** Slight luminance nudge from employee_id so teammates in the same role still differ. */
function nudgeHex(hex: string, delta: number): string {
  const raw = hex.replace('#', '');
  if (raw.length !== 6) {
    return hex;
  }
  const parts = [0, 2, 4].map((offset) => {
    const channel = Number.parseInt(raw.slice(offset, offset + 2), 16);
    return Math.max(0, Math.min(255, channel + delta));
  });
  return `#${parts.map((n) => n.toString(16).padStart(2, '0')).join('')}`;
}

export function employeeInitials(name: string | null | undefined): string {
  const cleaned = (name ?? '').trim();
  if (!cleaned) {
    return '?';
  }
  const parts = cleaned.split(/\s+/).filter(Boolean);
  if (parts.length === 1) {
    return parts[0].slice(0, 2).toUpperCase();
  }
  return `${parts[0][0] ?? ''}${parts[1][0] ?? ''}`.toUpperCase();
}

export function employeeIsLead(employee: CompanyEmployeeRecord): boolean {
  return Boolean(employee.primary) || (employee.role ?? '').trim().toLowerCase() === 'lead';
}

export function employeePresenceTone(
  employee: CompanyEmployeeRecord,
  options?: { liveBusy?: boolean; handoffWaiting?: boolean },
): EmployeePresenceTone {
  // Live IDE/stream ownership wins over a stale last-shift failure — otherwise a
  // teammate mid-run keeps a red ring and never shows the busy border.
  if (options?.liveBusy) {
    return 'working';
  }
  if (employeeFailureLine(employee)) {
    return employeeShiftNeedsContinuation(employee) ? 'interrupted' : 'failed';
  }
  if (!employee.enabled) {
    return 'paused';
  }
  // A completed Lead task can still be waiting on a real operator decision.
  // This takes precedence over generic busy/idle state so the roster remains
  // a visible route back to the Ask Card.
  if (employee.pending_decision_id) {
    return 'approval';
  }
  if (employeeIsActivelyBusy(employee)) {
    return 'working';
  }
  // Lead mirrors workspace executing — ignore that for personal presence unless liveBusy.
  if (employeeIsLead(employee) && !options?.handoffWaiting) {
    return 'idle';
  }
  const status = (employee.status ?? '').trim();
  // Assigned / Manual waiting handoff — amber ring, not green busy.
  if (options?.handoffWaiting || status === 'assigned') {
    return 'handoff';
  }
  // Always-on "watching" is on-duty, not mid-shift busy — keep idle ring.
  if (employeeIsWorking(status) && status !== 'watching') {
    return 'working';
  }
  return 'idle';
}

export function buildEmployeeAvatar(
  employee: CompanyEmployeeRecord,
  options?: { liveBusy?: boolean; handoffWaiting?: boolean },
): EmployeeAvatarModel {
  const glow = employeeGlowTone(employee);
  const base = ROLE_PALETTE[glow] ?? ROLE_PALETTE.default;
  const seed = `${employee.employee_id}:${employee.role}:${employee.name}`;
  const nudge = (hashSeed(seed) % 25) - 12;
  const lead = employeeIsLead(employee);
  return {
    initials: employeeInitials(employee.name),
    background: lead ? '#1e3a5f' : nudgeHex(base.background, nudge),
    foreground: lead ? '#ffe9a8' : base.foreground,
    glow,
    presence: employeePresenceTone(employee, options),
    lead,
    faceUrl: buildEmployeeFaceAvatarUrl(seed, { lead }),
  };
}
