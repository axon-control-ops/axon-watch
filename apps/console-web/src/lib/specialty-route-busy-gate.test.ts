import { describe, expect, it } from 'vitest';

import {
  isNamedAssignSpecialtyRoute,
  shouldApplySpecialtyRouteNow,
} from './specialty-route-busy-gate';

describe('specialty-route-busy-gate', () => {
  it('detects named-assign reasons', () => {
    expect(isNamedAssignSpecialtyRoute('named_assign_role_integrations')).toBe(true);
    expect(isNamedAssignSpecialtyRoute('role_integrations')).toBe(false);
  });

  it('skips soft specialty route when the destination is busy', () => {
    expect(
      shouldApplySpecialtyRouteNow({
        decision: {
          shouldRoute: true,
          reason: 'role_integrations',
          employee: { employee_id: 'soren' },
        },
        busyEmployeeIds: ['soren'],
      }),
    ).toBe(false);
  });

  it('applies soft specialty route when the destination is idle', () => {
    expect(
      shouldApplySpecialtyRouteNow({
        decision: {
          shouldRoute: true,
          reason: 'role_integrations',
          employee: { employee_id: 'soren' },
        },
        busyEmployeeIds: ['priya'],
      }),
    ).toBe(true);
  });

  it('still routes explicit named assigns onto a busy teammate', () => {
    expect(
      shouldApplySpecialtyRouteNow({
        decision: {
          shouldRoute: true,
          reason: 'named_assign_role_integrations',
          employee: { employee_id: 'soren' },
        },
        busyEmployeeIds: ['soren'],
      }),
    ).toBe(true);
  });

  it('does not apply when the decision says not to route', () => {
    expect(
      shouldApplySpecialtyRouteNow({
        decision: {
          shouldRoute: false,
          reason: 'score_too_low',
          employee: { employee_id: 'soren' },
        },
        busyEmployeeIds: [],
      }),
    ).toBe(false);
  });
});
