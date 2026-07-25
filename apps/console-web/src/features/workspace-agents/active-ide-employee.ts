import type { CompanyEmployeeRecord } from '../../contracts/canonical';
import type { WorkspaceChatThreadListItem } from '../../api/chat-api';

import { employeeInitials } from './employee-avatar';
import {
  employeeFailureDetailTooltip,
  employeeFailureLine,
  employeeIsActivelyBusy,
} from './company-roster-view';

export type ActiveIdeEmployeeView = {
  employee_id: string;
  name: string;
  role: string;
  role_label: string;
  azure_voice_id: string | null;
  initials: string;
};

function parseTitleName(title: string | null | undefined): string | null {
  const cleaned = (title ?? '').trim();
  if (!cleaned) {
    return null;
  }
  const [namePart] = cleaned.split(/\s*[·•|—-]\s*/);
  const name = (namePart ?? '').trim();
  return name || null;
}

/** Full roster row for the teammate bound to an IDE thread, when present. */
export function resolveActiveIdeEmployeeRecord(input: {
  thread: Pick<WorkspaceChatThreadListItem, 'employee_id'> | null;
  employees: readonly CompanyEmployeeRecord[];
}): CompanyEmployeeRecord | null {
  const employeeId = input.thread?.employee_id?.trim() ?? '';
  if (!employeeId) {
    return null;
  }
  return input.employees.find((row) => row.employee_id === employeeId) ?? null;
}

/** Map teammate thread ids to last-shift failure hints for tab chrome and history menus. */
export function buildIdeThreadFailureHintMap(input: {
  threads: readonly Pick<WorkspaceChatThreadListItem, 'thread_id' | 'employee_id'>[];
  employees: readonly CompanyEmployeeRecord[];
}): Map<string, string> {
  const hints = new Map<string, string>();
  for (const thread of input.threads) {
    const hint = resolveIdeThreadEmployeeFailure({ thread, employees: input.employees });
    if (hint) {
      hints.set(thread.thread_id, hint);
    }
  }
  return hints;
}

/** Full failure detail for thread tab/history hover when the compact hint truncates. */
export function resolveIdeThreadEmployeeFailureDetailTooltip(input: {
  thread: Pick<WorkspaceChatThreadListItem, 'employee_id'> | null;
  employees: readonly CompanyEmployeeRecord[];
}): string | null {
  const row = resolveActiveIdeEmployeeRecord(input);
  if (!row) {
    return null;
  }
  return employeeFailureDetailTooltip(row) ?? resolveIdeThreadEmployeeFailure(input);
}

/** Map teammate thread ids to full failure detail tooltips for tab chrome. */
export function buildIdeThreadFailureDetailTooltipMap(input: {
  threads: readonly Pick<WorkspaceChatThreadListItem, 'thread_id' | 'employee_id'>[];
  employees: readonly CompanyEmployeeRecord[];
}): Map<string, string> {
  const tooltips = new Map<string, string>();
  for (const thread of input.threads) {
    const tooltip = resolveIdeThreadEmployeeFailureDetailTooltip({
      thread,
      employees: input.employees,
    });
    if (tooltip) {
      tooltips.set(thread.thread_id, tooltip);
    }
  }
  return tooltips;
}

/** Keep roster dock selection aligned when switching teammate-owned IDE chat tabs. */
export function resolveRosterSelectionForIdeThread(input: {
  threadEmployeeId: string | null | undefined;
  employees: readonly CompanyEmployeeRecord[];
  currentSelectionId: string | null;
}): string | null {
  const employeeId = (input.threadEmployeeId ?? '').trim();
  if (!employeeId) {
    return input.currentSelectionId;
  }
  const known = input.employees.some((row) => row.employee_id === employeeId);
  if (!known) {
    return input.currentSelectionId;
  }
  return employeeId;
}

/** Last-shift failure line for a teammate-owned IDE thread, when roster says they need attention. */
export function resolveIdeThreadEmployeeFailure(input: {
  thread: Pick<WorkspaceChatThreadListItem, 'employee_id'> | null;
  employees: readonly CompanyEmployeeRecord[];
}): string | null {
  const employeeId = input.thread?.employee_id?.trim() ?? '';
  if (!employeeId) {
    return null;
  }
  const row = resolveActiveIdeEmployeeRecord(input);
  if (!row) {
    return null;
  }
  return employeeFailureLine(row);
}

/** True when the teammate owning this thread is mid-shift (or live-stream busy). */
export function resolveIdeThreadEmployeeBusy(input: {
  thread: Pick<WorkspaceChatThreadListItem, 'employee_id'> | null;
  employees: readonly CompanyEmployeeRecord[];
  liveBusyEmployeeIds?: readonly string[];
}): boolean {
  const employeeId = input.thread?.employee_id?.trim() ?? '';
  if (!employeeId) {
    return false;
  }
  if ((input.liveBusyEmployeeIds ?? []).includes(employeeId)) {
    return true;
  }
  const row = resolveActiveIdeEmployeeRecord(input);
  return row ? employeeIsActivelyBusy(row) : false;
}

/** Map teammate thread ids that should glow as busy in the conversation tabbar. */
export function buildIdeThreadBusySet(input: {
  threads: readonly Pick<WorkspaceChatThreadListItem, 'thread_id' | 'employee_id'>[];
  employees: readonly CompanyEmployeeRecord[];
  liveBusyEmployeeIds?: readonly string[];
}): Set<string> {
  const busy = new Set<string>();
  for (const thread of input.threads) {
    if (
      resolveIdeThreadEmployeeBusy({
        thread,
        employees: input.employees,
        liveBusyEmployeeIds: input.liveBusyEmployeeIds,
      })
    ) {
      busy.add(thread.thread_id);
    }
  }
  return busy;
}

/** Resolve the teammate bound to the active IDE thread (roster first, thread title fallback). */
export function resolveActiveIdeEmployee(input: {
  thread: Pick<
    WorkspaceChatThreadListItem,
    'employee_id' | 'employee_role' | 'title' | 'preview_label'
  > | null;
  employees: readonly CompanyEmployeeRecord[];
}): ActiveIdeEmployeeView | null {
  const employeeId = input.thread?.employee_id?.trim() ?? '';
  if (!employeeId) {
    return null;
  }

  const fromRoster = input.employees.find((row) => row.employee_id === employeeId);
  if (fromRoster) {
    return {
      employee_id: fromRoster.employee_id,
      name: fromRoster.name.trim() || 'Teammate',
      role: fromRoster.role,
      role_label: fromRoster.role_label,
      azure_voice_id: fromRoster.azure_voice_id?.trim() || null,
      initials: employeeInitials(fromRoster.name),
    };
  }

  const titleName =
    parseTitleName(input.thread?.title) ?? parseTitleName(input.thread?.preview_label);
  const name = titleName || 'Teammate';
  const role = (input.thread?.employee_role ?? '').trim() || 'agent';
  return {
    employee_id: employeeId,
    name,
    role,
    role_label: role,
    azure_voice_id: null,
    initials: employeeInitials(name),
  };
}
