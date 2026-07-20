import { describe, expect, it } from 'vitest';

import type { CompanyEmployeeRecord } from '../../contracts/canonical';
import {
  buildEmployeeAvatar,
  employeeInitials,
  employeePresenceTone,
} from './employee-avatar';

function employee(overrides: Partial<CompanyEmployeeRecord> = {}): CompanyEmployeeRecord {
  return {
    employee_id: 'employee-workspace_axon_watch-frontend-2',
    workspace_id: 'workspace_axon_watch',
    name: 'Jules',
    role: 'frontend',
    role_label: 'Frontend',
    schedule: 'continuous',
    schedule_label: 'Continuous',
    status: 'idle',
    owns: 'console UI/UX',
    enabled: true,
    primary: false,
    ...overrides,
  };
}

describe('employee-avatar', () => {
  it('builds stable two-letter initials', () => {
    expect(employeeInitials('Jules')).toBe('JU');
    expect(employeeInitials('Mira Lane')).toBe('ML');
    expect(employeeInitials('')).toBe('?');
  });

  it('is deterministic for the same employee', () => {
    const row = employee();
    expect(buildEmployeeAvatar(row)).toEqual(buildEmployeeAvatar(row));
  });

  it('maps presence tone from status / failure / pause', () => {
    expect(employeePresenceTone(employee({ status: 'executing' }))).toBe('working');
    expect(
      employeePresenceTone(
        employee({
          status: 'idle',
          last_outcome: 'failed',
          last_outcome_detail: 'timeout',
        }),
      ),
    ).toBe('failed');
    expect(employeePresenceTone(employee({ enabled: false }))).toBe('paused');
    expect(
      employeePresenceTone(
        employee({
          enabled: false,
          status: 'idle',
          last_outcome: 'failed',
          last_outcome_detail: 'timeout',
        }),
      ),
    ).toBe('failed');
    expect(employeePresenceTone(employee({ status: 'idle' }))).toBe('idle');
  });

  it('keeps role-tinted backgrounds distinct across roles', () => {
    const frontend = buildEmployeeAvatar(employee({ role: 'frontend', name: 'Jules' }));
    const backend = buildEmployeeAvatar(
      employee({
        employee_id: 'employee-workspace_axon_watch-backend-3',
        role: 'backend',
        name: 'Reed',
      }),
    );
    expect(frontend.glow).toBe('frontend');
    expect(backend.glow).toBe('backend');
    expect(frontend.background).not.toBe(backend.background);
  });
});
