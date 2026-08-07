import { describe, expect, it } from 'vitest';

import type { CompanyEmployeeRecord } from '../../contracts/canonical';
import {
  companyBusyEmployeesCount,
  employeeIsActivelyBusy,
  resolveLiveBusyEmployeeIds,
  resolveReportingEmployeeId,
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

  it('does not treat Lead mirrored workspace executing as personal busy', () => {
    const lead = employee({
      employee_id: 'employee-workspace_dashpro-lead-0',
      name: 'Dana',
      role: 'lead',
      primary: true,
      status: 'executing',
      active_run_id: undefined,
    });
    expect(employeeIsActivelyBusy(lead)).toBe(false);
    expect(employeeIsActivelyBusy({ ...lead, active_run_id: 'run_lead' })).toBe(true);
  });

  it('treats watching specialists with an active run as busy', () => {
    const watcher = employee({
      status: 'watching',
      active_run_id: 'run_continuous',
    });
    expect(employeeIsActivelyBusy(watcher)).toBe(true);
    expect(companyBusyEmployeesCount([watcher])).toBe(1);
  });

  it('counts every streaming thread owner as live-busy, not only the focused tab', () => {
    const sipho = employee({
      employee_id: 'sipho',
      name: 'Sipho',
      role: 'backend',
      status: 'idle',
      last_outcome: 'failed',
      last_outcome_detail: 'usage limits',
    });
    const amara = employee({
      employee_id: 'amara',
      name: 'Amara',
      role: 'integrations',
      status: 'idle',
      last_outcome: 'failed',
      last_outcome_detail: 'usage limits',
    });
    const ids = resolveLiveBusyEmployeeIds({
      employees: [sipho, amara],
      streamingThreadIds: ['thread_sipho', 'thread_amara'],
      threads: [
        { thread_id: 'thread_sipho', employee_id: 'sipho' },
        { thread_id: 'thread_amara', employee_id: 'amara' },
      ],
      focusedStreamEmployeeId: 'sipho',
    });
    expect(ids.sort()).toEqual(['amara', 'sipho']);
  });

  describe('resolveReportingEmployeeId', () => {
    it('returns the focused thread owner while a stream is active', () => {
      const result = resolveReportingEmployeeId({
        agentStreamActive: true,
        activeThreadEmployeeId: 'dana',
      });
      expect(result).toBe('dana');
    });

    it('returns null when no stream is active, even with a focused thread', () => {
      const result = resolveReportingEmployeeId({
        agentStreamActive: false,
        activeThreadEmployeeId: 'dana',
      });
      expect(result).toBeNull();
    });

    it('falls back to a background-tab streaming thread owner', () => {
      const result = resolveReportingEmployeeId({
        agentStreamActive: false,
        activeThreadEmployeeId: null,
        streamingThreadIds: ['thread_soren'],
        threads: [
          { thread_id: 'thread_dana', employee_id: 'dana' },
          { thread_id: 'thread_soren', employee_id: 'soren' },
        ],
      });
      expect(result).toBe('soren');
    });

    it('prefers the focused stream over a background streaming thread', () => {
      const result = resolveReportingEmployeeId({
        agentStreamActive: true,
        activeThreadEmployeeId: 'dana',
        streamingThreadIds: ['thread_soren'],
        threads: [{ thread_id: 'thread_soren', employee_id: 'soren' }],
      });
      expect(result).toBe('dana');
    });

    it('returns null when nothing is streaming', () => {
      const result = resolveReportingEmployeeId({
        agentStreamActive: false,
        activeThreadEmployeeId: null,
        streamingThreadIds: [],
        threads: [],
      });
      expect(result).toBeNull();
    });

    it('ignores a streaming thread id with no matching thread record', () => {
      const result = resolveReportingEmployeeId({
        agentStreamActive: false,
        streamingThreadIds: ['thread_unknown'],
        threads: [{ thread_id: 'thread_dana', employee_id: 'dana' }],
      });
      expect(result).toBeNull();
    });
  });
});
