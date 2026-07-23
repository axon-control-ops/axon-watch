import { beforeEach, describe, expect, it, vi } from 'vitest';

import {
  applyEmployeeSpecialtyRoute,
  undoEmployeeSpecialtyRoute,
  type SpecialtyRouteShell,
} from './apply-employee-specialty-route';
import type { TeammateRouteEmployee } from './composer-teammate-route';
import {
  clearTeammateRouteNotice,
  teammateRouteNotice,
} from './teammate-route-notice';

const marco: TeammateRouteEmployee = {
  employee_id: 'marco',
  name: 'Marco',
  role: 'backend',
  role_label: 'Backend',
  owns: 'APIs and services',
};
const priya: TeammateRouteEmployee = {
  employee_id: 'priya',
  name: 'Priya',
  role: 'frontend',
  role_label: 'Frontend',
  owns: 'UI and screens',
};

function shell(): SpecialtyRouteShell {
  return {
    activeIdeThreadId: 'thread-marco',
    activeIdeEmployeeRecord: marco,
    companyEmployeesForCurrentWorkspace: [marco, priya],
    openOrFocusEmployeeIdeThread: vi.fn(async (employee) => `thread-${employee.employee_id}`),
    selectIdeThread: vi.fn(async () => undefined),
    createIdeThread: vi.fn(async () => 'thread-generic'),
  };
}

describe('applyEmployeeSpecialtyRoute', () => {
  beforeEach(clearTeammateRouteNotice);

  it('opens the owning thread and records reversible route metadata', async () => {
    const target = shell();
    const result = await applyEmployeeSpecialtyRoute(target, {
      shouldRoute: true,
      reason: 'role_frontend',
      employee: priya,
      fromEmployeeId: marco.employee_id,
      fromName: marco.name,
      source: 'deterministic',
    });

    expect(result.routed).toBe(true);
    expect(target.openOrFocusEmployeeIdeThread).toHaveBeenCalledWith(priya);
    expect(teammateRouteNotice.value).toMatchObject({
      toName: 'Priya',
      fromName: 'Marco',
      previousEmployeeId: 'marco',
      previousThreadId: 'thread-marco',
    });
  });

  it('undo restores the previous employee thread without cancelling work', async () => {
    const target = shell();
    await applyEmployeeSpecialtyRoute(target, {
      shouldRoute: true,
      reason: 'role_frontend',
      employee: priya,
      fromEmployeeId: marco.employee_id,
      fromName: marco.name,
    });

    await undoEmployeeSpecialtyRoute(target);

    expect(target.openOrFocusEmployeeIdeThread).toHaveBeenLastCalledWith(marco);
    expect(teammateRouteNotice.value).toBeNull();
  });
});
