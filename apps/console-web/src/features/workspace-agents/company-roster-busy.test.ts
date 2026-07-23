import { describe, expect, it } from 'vitest';

import type { CompanyEmployeeRecord } from '../../contracts/canonical';
import {
  companyBusyEmployeesCount,
  employeeIsActivelyBusy,
} from './company-roster-busy';
import { employeeIsWorking } from './company-roster-status';

function employee(overrides: Partial<CompanyEmployeeRecord> = {}): CompanyEmployeeRecord {
  return {
    employee_id: 'e1',
    workspace_id: 'workspace_dashpro',
    name: 'Alex',
    role: 'backend',
    role_label: 'Backend',
    schedule: 'continuous',
    schedule_label: 'Continuous',
    status: 'idle',
    owns: 'APIs',
    enabled: true,
    primary: false,
    ...overrides,
  };
}

describe('company-roster-busy', () => {
  it('does not treat assigned fan-out runs as busy chrome', () => {
    const assigned = employee({
      employee_id: 'employee-workspace_dashpro-backend-3',
      name: 'Marco',
      role: 'backend',
      status: 'assigned',
      active_run_id: 'run_queued_fanout',
    });
    expect(employeeIsActivelyBusy(assigned)).toBe(false);
    expect(employeeIsWorking(assigned.status)).toBe(true);
    expect(companyBusyEmployeesCount([assigned])).toBe(0);
  });

  it('treats executing specialists with active runs as busy', () => {
    const specialist = employee({
      status: 'executing',
      active_run_id: 'run_soren',
    });
    expect(employeeIsActivelyBusy(specialist)).toBe(true);
    expect(companyBusyEmployeesCount([specialist])).toBe(1);
  });
});
