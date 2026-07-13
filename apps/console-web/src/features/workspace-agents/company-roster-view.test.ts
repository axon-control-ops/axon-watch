import { describe, expect, it } from 'vitest';

import {
  companyHeadline,
  employeeMetaLine,
  employeeStatusLabel,
} from './company-roster-view';

describe('company-roster-view', () => {
  it('formats employee meta and status labels', () => {
    expect(
      employeeMetaLine({
        employee_id: 'e1',
        workspace_id: 'workspace_demo',
        name: 'Night Watch',
        role: 'watcher',
        role_label: 'Night Watch',
        schedule: 'always_on',
        schedule_label: 'Always on (24/7)',
        status: 'watching',
        owns: 'signals',
        enabled: true,
        primary: false,
      }),
    ).toBe('Night Watch · Always on (24/7)');
    expect(employeeStatusLabel('waiting_approval')).toBe('waiting approval');
  });

  it('builds company headline with employee count', () => {
    expect(companyHeadline('Axon-X', 5)).toBe('Axon-X · 5 employees');
    expect(companyHeadline('Solo', 1)).toBe('Solo · 1 employee');
  });
});
