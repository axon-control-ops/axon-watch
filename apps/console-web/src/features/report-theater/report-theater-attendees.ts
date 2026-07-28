import type { CompanyEmployeeRecord } from '../../contracts/canonical';
import { buildEmployeeAvatar, employeeIsLead, type EmployeeAvatarModel } from '../workspace-agents/employee-avatar';
import { resolveVaxonAvatarUrl } from '../../lib/vaxon-avatar-view';
import { OPERATOR_PERSONA_NAME } from '../../lib/operator-persona-name';

export type ReportTheaterAttendee = {
  id: string;
  name: string;
  roleLabel: string;
  kind: 'vaxon' | 'employee';
  lead: boolean;
  avatar: Pick<EmployeeAvatarModel, 'initials' | 'background' | 'foreground' | 'faceUrl'>;
  /** Highlighted when the active stage mentions this person. */
  speaking: boolean;
  statusLine: string;
};

function mentionedInLines(name: string, lines: string[]): boolean {
  const needle = name.trim().toLowerCase();
  if (!needle) {
    return false;
  }
  const first = needle.split(/\s+/)[0] ?? needle;
  return lines.some((line) => {
    const hay = line.toLowerCase();
    return hay.includes(needle) || (first.length > 2 && hay.includes(first));
  });
}

function employeeStatus(employee: CompanyEmployeeRecord): string {
  const status = String(employee.status || '').replace(/_/g, ' ').trim();
  if (employee.active_run_id) {
    return status || 'working';
  }
  if (String(employee.last_outcome || '').toLowerCase() === 'completed') {
    return 'just wrapped';
  }
  if (String(employee.last_outcome || '').toLowerCase() === 'failed') {
    return 'needs follow-up';
  }
  if (employeeIsLead(employee)) {
    return 'Lead present';
  }
  return status || 'present';
}

/**
 * Build the stand-up gallery: VAXON chairs, Leads flank, then working / named teammates.
 */
export function buildReportTheaterAttendees(input: {
  employees: CompanyEmployeeRecord[];
  activeLines: string[];
  /** When Lead rollups is on stage, keep Leads highlighted as speakers. */
  stageId?: string | null;
  max?: number;
}): ReportTheaterAttendee[] {
  const max = Math.max(4, input.max ?? 7);
  const lines = input.activeLines;
  const leadStage = input.stageId === 'lead_rollups';
  const ranked = [...input.employees].sort((left, right) => {
    const leftLead = employeeIsLead(left) ? 0 : 1;
    const rightLead = employeeIsLead(right) ? 0 : 1;
    if (leftLead !== rightLead) {
      return leftLead - rightLead;
    }
    const leftMention = mentionedInLines(left.name, lines) ? 0 : 1;
    const rightMention = mentionedInLines(right.name, lines) ? 0 : 1;
    if (leftMention !== rightMention) {
      return leftMention - rightMention;
    }
    const leftBusy = left.active_run_id ? 0 : 1;
    const rightBusy = right.active_run_id ? 0 : 1;
    if (leftBusy !== rightBusy) {
      return leftBusy - rightBusy;
    }
    return left.name.localeCompare(right.name);
  });

  const people = ranked.slice(0, max - 1).map((employee) => {
    const avatar = buildEmployeeAvatar(employee);
    const lead = employeeIsLead(employee);
    const speaking =
      mentionedInLines(employee.name, lines) || (leadStage && lead);
    return {
      id: employee.employee_id,
      name: employee.name,
      roleLabel: employee.role_label || employee.role || 'Teammate',
      kind: 'employee' as const,
      lead,
      avatar: {
        initials: avatar.initials,
        background: avatar.background,
        foreground: avatar.foreground,
        faceUrl: avatar.faceUrl,
      },
      speaking,
      statusLine: speaking && leadStage && lead ? 'reporting' : employeeStatus(employee),
    };
  });

  return [
    {
      id: 'vaxon',
      name: OPERATOR_PERSONA_NAME,
      roleLabel: 'Chair',
      kind: 'vaxon',
      lead: true,
      avatar: {
        initials: 'VX',
        background: '#123a5c',
        foreground: '#d7f6ff',
        faceUrl: resolveVaxonAvatarUrl(),
      },
      speaking: !leadStage,
      statusLine: leadStage ? 'listening' : 'briefing',
    },
    ...people,
  ];
}
