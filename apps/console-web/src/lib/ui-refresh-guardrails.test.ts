import { describe, expect, it } from 'vitest';

import type { CompanyEmployeeRecord } from '../contracts/canonical';
import {
  COMPANY_REFRESH_MS,
  companyEmployeesFingerprint,
  companyEmployeesUnchanged,
} from './ui-refresh-guardrails';

function employee(overrides: Partial<CompanyEmployeeRecord> = {}): CompanyEmployeeRecord {
  return {
    employee_id: 'e1',
    workspace_id: 'workspace_demo',
    name: 'Jules',
    role: 'frontend',
    role_label: 'UI/UX',
    schedule: 'continuous',
    schedule_label: 'Continuous',
    status: 'idle',
    owns: 'console',
    enabled: true,
    primary: false,
    ...overrides,
  };
}

describe('ui-refresh-guardrails', () => {
  it('keeps roster poll interval at a calm cadence', () => {
    expect(COMPANY_REFRESH_MS).toBeGreaterThanOrEqual(20_000);
  });

  it('fingerprints employees so identical polls are skipped', () => {
    const left = [
      employee({
        last_outcome: 'failed',
        last_outcome_detail: 'timeout',
        status: 'watching',
      }),
    ];
    const right = [
      employee({
        last_outcome: 'failed',
        last_outcome_detail: 'timeout',
        status: 'watching',
      }),
    ];
    expect(companyEmployeesFingerprint(left)).toBe(companyEmployeesFingerprint(right));
    expect(companyEmployeesUnchanged(left, right)).toBe(true);
    expect(
      companyEmployeesUnchanged(left, [
        employee({
          last_outcome: 'failed',
          last_outcome_detail: 'timeout',
          status: 'idle',
        }),
      ]),
    ).toBe(false);
  });
});
