import { describe, expect, it } from 'vitest';

import type { CompanyEmployeeRecord } from '../../contracts/canonical';
import {
  buildCompanyRosterAlertBadge,
  companyFailedEmployeesHint,
  employeeDisplayStatus,
  employeeFailureDetailTooltip,
  employeeFailureLine,
} from './company-roster-failure-view';

function employee(overrides: Partial<CompanyEmployeeRecord> = {}): CompanyEmployeeRecord {
  return {
    employee_id: 'e1',
    workspace_id: 'workspace_demo',
    name: 'Marco',
    role: 'backend',
    role_label: 'Backend',
    schedule: 'continuous',
    schedule_label: 'Continuous',
    status: 'idle',
    owns: 'APIs and persistence',
    enabled: true,
    primary: false,
    ...overrides,
  };
}

describe('Gate 6 confidence and roster status', () => {
  it('shows an authoritative delivery block instead of a confidence success', () => {
    const gateBlocked = employee({
      last_outcome: 'failed',
      last_outcome_detail:
        'Lane B finalization failed: review_ready/complete blocked: acceptance_evidence did not pass (Gate 6)',
    });

    expect(employeeFailureLine(gateBlocked)).toContain('Delivery blocked by AXON-X');
    expect(employeeFailureLine(gateBlocked)).toContain('self-assessment, not a pass signal');
    expect(employeeFailureDetailTooltip(gateBlocked)).toContain('Gate 6 is authoritative');
    expect(employeeDisplayStatus(gateBlocked)).toBe('blocked');
    expect(buildCompanyRosterAlertBadge([gateBlocked])).toMatchObject({
      label: '1 blocked',
      tone: 'blocked',
    });
  });

  it('labels an all-Gate-6 fleet as blocked instead of failed', () => {
    const blockedDetail = 'acceptance_evidence did not pass (Gate 6)';
    const blocked = [
      employee({ employee_id: 'e1', last_outcome: 'failed', last_outcome_detail: blockedDetail }),
      employee({ employee_id: 'e2', last_outcome: 'failed', last_outcome_detail: blockedDetail }),
    ];

    expect(buildCompanyRosterAlertBadge(blocked)).toMatchObject({
      label: '2 blocked',
      tone: 'blocked',
    });
    expect(companyFailedEmployeesHint(blocked)).toContain('delivery blocked by Gate 6');
  });
});
