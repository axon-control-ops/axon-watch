import { describe, expect, it } from 'vitest';

import type { CompanyEmployeeRecord } from '../../contracts/canonical';
import { employeeIdeThreadTitle } from './employee-thread';

function employee(overrides: Partial<CompanyEmployeeRecord> = {}): CompanyEmployeeRecord {
  return {
    employee_id: 'employee-workspace_axon_watch-integrations-4',
    workspace_id: 'workspace_axon_watch',
    name: 'Quinn',
    role: 'integrations',
    role_label: 'Integrations',
    schedule: 'continuous',
    schedule_label: 'Continuous',
    status: 'idle',
    owns: 'connectors',
    enabled: true,
    primary: false,
    ...overrides,
  };
}

describe('employee-thread', () => {
  it('builds a tab title from name and role badge', () => {
    expect(employeeIdeThreadTitle(employee())).toBe('Quinn · Integrations');
  });
});
