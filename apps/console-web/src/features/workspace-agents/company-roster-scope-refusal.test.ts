import { describe, expect, it } from 'vitest';

import type { CompanyEmployeeRecord } from '../../contracts/canonical';
import { companyHasFailedEmployees, employeeFailureLine } from './company-roster-failure-view';

describe('company roster scope refusal', () => {
  it('preserves the receipt without branding the worker failed', () => {
    const employee: CompanyEmployeeRecord = {
      employee_id: 'marco', workspace_id: 'workspace_dashpro', name: 'Marco',
      role: 'backend', role_label: 'Backend', schedule: 'continuous',
      schedule_label: 'Continuous', status: 'idle', owns: 'APIs', enabled: true,
      primary: false, last_outcome: 'failed',
      last_outcome_detail: 'Continuous worker scope guard tripped: outside allowed paths.',
    };
    expect(employeeFailureLine(employee)).toBeNull();
    expect(companyHasFailedEmployees([employee])).toBe(false);
  });
});
