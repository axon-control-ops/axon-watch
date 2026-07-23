import { beforeEach, describe, expect, it, vi } from 'vitest';

import routeCases from '../../../../packages/shared-types/fixtures/teammate-route-cases.json';
import type { SpecialtyRouteShell } from './apply-employee-specialty-route';
import type { TeammateRouteEmployee } from './composer-teammate-route';
import { routeEmployeeSpecialtyTask } from './route-employee-specialty-task';
import { clearTeammateRouteNotice } from './teammate-route-notice';

const roster = routeCases.roster satisfies TeammateRouteEmployee[];

describe('routeEmployeeSpecialtyTask', () => {
  beforeEach(clearTeammateRouteNotice);

  it('opens Priya before restoring and submitting a Brain handoff', async () => {
    const order: string[] = [];
    const shell: SpecialtyRouteShell = {
      activeIdeThreadId: 'generic-thread',
      activeIdeEmployeeRecord: null,
      companyEmployeesForCurrentWorkspace: roster,
      openOrFocusEmployeeIdeThread: vi.fn(async (employee) => {
        order.push(`open:${employee.name}`);
        return 'thread-priya';
      }),
      selectIdeThread: vi.fn(async () => undefined),
      createIdeThread: vi.fn(async () => 'thread-generic'),
    };

    const result = await routeEmployeeSpecialtyTask({
      shell,
      prompt: 'Fix the enrollment confirmation UI card.',
      workspaceId: 'workspace_dashpro',
      currentEmployee: null,
      roster,
      restorePrompt: () => {
        order.push('restore');
      },
      submit: async () => {
        order.push('submit');
      },
    });

    expect(result.decision.employee?.name).toBe('Priya');
    expect(result.submitted).toBe(true);
    expect(order).toEqual(['open:Priya', 'restore', 'submit']);
  });

  it('honors a Brain-selected employee hint without a second classifier call', async () => {
    const opened: string[] = [];
    const shell: SpecialtyRouteShell = {
      activeIdeThreadId: 'generic-thread',
      activeIdeEmployeeRecord: null,
      companyEmployeesForCurrentWorkspace: roster,
      openOrFocusEmployeeIdeThread: vi.fn(async (employee) => {
        opened.push(employee.name);
        return `thread-${employee.employee_id}`;
      }),
      selectIdeThread: vi.fn(async () => undefined),
    };

    const result = await routeEmployeeSpecialtyTask({
      shell,
      prompt: 'Investigate this issue.',
      workspaceId: 'workspace_dashpro',
      currentEmployee: null,
      roster,
      preferredEmployeeId: 'employee-workspace_dashpro-backend-3',
      restorePrompt: vi.fn(),
    });

    expect(result.decision.source).toBe('model');
    expect(opened).toEqual(['Marco']);
  });
});
