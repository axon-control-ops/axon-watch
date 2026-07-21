/**
 * Shared applicator: open owning teammate thread + set Undo notice.
 */

import type { TeammateRouteDecision, TeammateRouteEmployee } from './composer-teammate-route';
import {
  clearTeammateRouteNotice,
  setTeammateRouteNotice,
  teammateRouteNotice,
  type TeammateRouteNotice,
} from './teammate-route-notice';

export type SpecialtyRouteShell = {
  activeIdeThreadId: string | null;
  activeIdeEmployeeRecord: TeammateRouteEmployee | null;
  companyEmployeesForCurrentWorkspace: readonly TeammateRouteEmployee[];
  openOrFocusEmployeeIdeThread: (employee: {
    employee_id: string;
    name: string;
    role: string;
    role_label?: string;
  }) => Promise<string | null>;
  selectIdeThread: (threadId: string) => Promise<void>;
  createIdeThread?: () => Promise<string | null>;
};

export type ApplySpecialtyRouteResult = {
  routed: boolean;
  notice: TeammateRouteNotice | null;
  threadId: string | null;
};

export function noticeFromDecision(
  decision: TeammateRouteDecision,
  previousEmployeeId: string,
  previousThreadId?: string | null,
): TeammateRouteNotice | null {
  if (!decision.shouldRoute || !decision.employee) {
    return null;
  }
  return {
    reason: decision.reason,
    toName: decision.employee.name.trim() || 'teammate',
    toRoleLabel:
      decision.employee.role_label?.trim() || decision.employee.role.trim() || 'role',
    fromName: decision.fromName?.trim() || (previousEmployeeId ? 'teammate' : 'workspace'),
    previousEmployeeId,
    previousThreadId: previousThreadId ?? null,
  };
}

export async function applyEmployeeSpecialtyRoute(
  shell: SpecialtyRouteShell,
  decision: TeammateRouteDecision,
): Promise<ApplySpecialtyRouteResult> {
  if (!decision.shouldRoute || !decision.employee) {
    return { routed: false, notice: null, threadId: null };
  }

  const previousEmployeeId =
    decision.fromEmployeeId?.trim() ||
    shell.activeIdeEmployeeRecord?.employee_id?.trim() ||
    '';
  const previousThreadId = shell.activeIdeThreadId;

  const opened = await shell.openOrFocusEmployeeIdeThread(decision.employee);
  if (!opened) {
    return { routed: false, notice: null, threadId: null };
  }

  const notice = noticeFromDecision(decision, previousEmployeeId, previousThreadId);
  if (notice) {
    setTeammateRouteNotice(notice);
  }
  return { routed: true, notice, threadId: opened };
}

export async function undoEmployeeSpecialtyRoute(
  shell: SpecialtyRouteShell,
  notice: TeammateRouteNotice | null = null,
): Promise<boolean> {
  const target = notice ?? teammateRouteNotice.value;
  clearTeammateRouteNotice();
  if (!target) {
    return false;
  }

  const previousId = target.previousEmployeeId?.trim() ?? '';
  if (previousId) {
    const previous = shell.companyEmployeesForCurrentWorkspace.find(
      (row) => row.employee_id === previousId,
    );
    if (previous) {
      const opened = await shell.openOrFocusEmployeeIdeThread(previous);
      return Boolean(opened);
    }
  }

  const previousThreadId = target.previousThreadId?.trim() ?? '';
  if (previousThreadId) {
    await shell.selectIdeThread(previousThreadId);
    return true;
  }

  if (shell.createIdeThread) {
    const created = await shell.createIdeThread();
    return Boolean(created);
  }
  return false;
}

export function dismissEmployeeSpecialtyRoute(): void {
  clearTeammateRouteNotice();
}
