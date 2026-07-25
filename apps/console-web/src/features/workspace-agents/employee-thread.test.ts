import { describe, expect, it } from 'vitest';

import type { CompanyEmployeeRecord } from '../../contracts/canonical';
import {
  currentEmployeeIdeThreadTitle,
  employeeIdeThreadTitle,
} from './employee-thread';

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

  it('uses the current roster name instead of a stale persisted thread title', () => {
    expect(
      currentEmployeeIdeThreadTitle(
        {
          employee_id: 'employee-workspace_axon_watch-integrations-4',
          preview_label: 'Jules · Integrations',
        },
        [employee({ name: 'Quinn' })],
      ),
    ).toBe('Quinn · Integrations');
  });

  it('keeps the thread label when no roster employee is bound', () => {
    expect(
      currentEmployeeIdeThreadTitle(
        {
          employee_id: null,
          preview_label: 'Can you review this?',
        },
        [employee()],
      ),
    ).toBe('Can you review this?');
  });
});
