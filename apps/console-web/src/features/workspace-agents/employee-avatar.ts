import type { CompanyEmployeeRecord } from '../../contracts/canonical';

import {
  employeeFailureLine,
  employeeGlowTone,
  employeeIsWorking,
  employeeShiftNeedsContinuation,
  type EmployeeGlowTone,
} from './company-roster-view';

export type EmployeePresenceTone = 'idle' | 'working' | 'failed' | 'interrupted' | 'paused';

export type EmployeeAvatarModel = {
  initials: string;
  background: string;
  foreground: string;
  glow: EmployeeGlowTone;
  presence: EmployeePresenceTone;
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

export function employeePresenceTone(employee: CompanyEmployeeRecord): EmployeePresenceTone {
  if (employeeFailureLine(employee)) {
    return employeeShiftNeedsContinuation(employee) ? 'interrupted' : 'failed';
  }
  if (!employee.enabled) {
    return 'paused';
  }
  if (employeeIsWorking(employee.status)) {
    return 'working';
  }
  return 'idle';
}

export function buildEmployeeAvatar(employee: CompanyEmployeeRecord): EmployeeAvatarModel {
  const glow = employeeGlowTone(employee);
  const base = ROLE_PALETTE[glow] ?? ROLE_PALETTE.default;
  const seed = `${employee.employee_id}:${employee.role}:${employee.name}`;
  const nudge = (hashSeed(seed) % 25) - 12;
  return {
    initials: employeeInitials(employee.name),
    background: nudgeHex(base.background, nudge),
    foreground: base.foreground,
    glow,
    presence: employeePresenceTone(employee),
  };
}
