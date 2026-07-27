import { describe, expect, it } from 'vitest';

import {
  companyHasWorkingEmployees,
  companyHeadline,
  employeeDockReceiptRunId,
  employeeDockReceiptRunLabel,
  employeeGlowTone,
  employeeIsActivelyBusy,
  employeeIsWorking,
  employeeMetaLine,
  adjacentPresenceStripEmployee,
  employeePresenceContextPhrase,
  employeePresenceSelectLabel,
  employeePresenceStripTitle,
  firstFailedRosterEmployee,
  pickDefaultRosterEmployee,
  presenceStripOptionId,
  selectedPresenceStripEmployee,
  employeeStatusLabel,
  employeeTalkLine,
  employeeSpeakLine,
  sortEmployeesForPresenceStrip,
} from './company-roster-view';
import type { CompanyEmployeeRecord } from '../../contracts/canonical';

function employee(overrides: Partial<CompanyEmployeeRecord> = {}): CompanyEmployeeRecord {
  return {
    employee_id: 'e1',
    workspace_id: 'workspace_demo',
    name: 'Shell Craft',
    role: 'frontend',
    role_label: 'UI/UX',
    schedule: 'continuous',
    schedule_label: 'Continuous',
    status: 'idle',
    owns: 'console UI/UX, dock, and shell polish',
    enabled: true,
    primary: false,
    ...overrides,
  };
}

describe('company-roster-view', () => {
  it('formats employee meta and status labels', () => {
    expect(
      employeeMetaLine({
        employee_id: 'e1',
        workspace_id: 'workspace_demo',
        name: 'Rowan',
        role: 'watcher',
        role_label: 'Watcher',
        schedule: 'always_on',
        schedule_label: 'Always on (24/7)',
        status: 'watching',
        owns: 'signals',
        enabled: true,
        primary: false,
      }),
    ).toBe('Always on (24/7)');
    expect(employeeStatusLabel('waiting_approval')).toBe('waiting approval');
    expect(employeeStatusLabel('failed')).toBe('last job failed');
    expect(employeeStatusLabel('interrupted')).toBe('job interrupted');
  });

  it('builds company headline with employee count', () => {
    expect(companyHeadline('Axon-X', 5)).toBe('Axon-X · 5 employees');
    expect(companyHeadline('Solo', 1)).toBe('Solo · 1 employee');
  });

  it('dedupes dock receipt run ids and labels', () => {
    const failed = employee({
      status: 'idle',
      last_outcome: 'failed',
      last_outcome_detail: 'vitest: assertion failed',
      last_run_id: 'run_failed_1',
    });
    expect(employeeDockReceiptRunId(failed)).toBe('run_failed_1');
    expect(employeeDockReceiptRunLabel('run_failed_1')).toBe('#failed');

    const ok = employee({
      status: 'idle',
      last_outcome: 'completed',
      last_outcome_detail: 'Shipped dock polish with receipts.',
      last_run_id: 'run_ok_1',
    });
    expect(employeeDockReceiptRunId(ok)).toBe('run_ok_1');
    expect(employeeDockReceiptRunLabel('run_ok_1')).toBe('#ok_1');
  });

  it('steps presence strip selection with keyboard moves', () => {
    const rows = [
      employee({ employee_id: 'e_idle', name: 'Zara', status: 'idle' }),
      employee({
        employee_id: 'e_failed',
        name: 'Mira',
        status: 'idle',
        last_outcome: 'failed',
        last_outcome_detail: 'timeout',
      }),
      employee({ employee_id: 'e_work', name: 'Alex', status: 'executing' }),
    ];
    const sorted = sortEmployeesForPresenceStrip(rows);
    expect(adjacentPresenceStripEmployee(rows, null, 'first')?.employee_id).toBe(
      sorted[0].employee_id,
    );
    expect(adjacentPresenceStripEmployee(rows, sorted[0].employee_id, 'next')?.employee_id).toBe(
      sorted[1].employee_id,
    );
    expect(adjacentPresenceStripEmployee(rows, sorted[0].employee_id, 'prev')?.employee_id).toBe(
      sorted[sorted.length - 1].employee_id,
    );
    expect(adjacentPresenceStripEmployee(rows, sorted[1].employee_id, 'last')?.employee_id).toBe(
      sorted[sorted.length - 1].employee_id,
    );
  });

  it('picks default roster selection with failed teammates first in strip order', () => {
    const rows = [
      employee({ employee_id: 'e_idle', name: 'Zara', status: 'idle' }),
      employee({
        employee_id: 'e_failed_b',
        name: 'Bravo',
        status: 'idle',
        last_outcome: 'failed',
        last_outcome_detail: 'build failed',
      }),
      employee({
        employee_id: 'e_failed_a',
        name: 'Alpha',
        status: 'idle',
        last_outcome: 'failed',
        last_outcome_detail: 'timeout',
      }),
      employee({ employee_id: 'e_lead', name: 'Lead', role: 'lead', primary: true, status: 'idle' }),
    ];
    expect(firstFailedRosterEmployee(rows)?.employee_id).toBe('e_failed_a');
    expect(pickDefaultRosterEmployee(rows)?.employee_id).toBe('e_failed_a');
    expect(pickDefaultRosterEmployee([rows[0], rows[3]])?.employee_id).toBe('e_lead');
    expect(pickDefaultRosterEmployee([rows[0]])?.employee_id).toBe('e_idle');
  });

  it('sorts presence strip with failed teammates first', () => {
    const rows = [
      employee({ employee_id: 'e_idle', name: 'Zara', status: 'idle' }),
      employee({
        employee_id: 'e_failed',
        name: 'Mira',
        status: 'idle',
        last_outcome: 'failed',
        last_outcome_detail: 'timeout',
      }),
      employee({ employee_id: 'e_work', name: 'Alex', status: 'executing' }),
      employee({ employee_id: 'e_lead', name: 'Lead', role: 'lead', primary: true, status: 'idle' }),
    ];
    expect(
      sortEmployeesForPresenceStrip(rows).map((row) => row.employee_id),
    ).toEqual(['e_failed', 'e_work', 'e_lead', 'e_idle']);
  });

  it('builds stable presence strip option ids', () => {
    expect(presenceStripOptionId('e_failed')).toBe('company-presence-option-e_failed');
    expect(presenceStripOptionId('')).toBe('');
    expect(presenceStripOptionId(null)).toBe('');
  });

  it('builds presence strip aria labels and titles for failure, pause, and live shifts', () => {
    const failed = employee({
      name: 'Jules',
      status: 'idle',
      last_outcome: 'failed',
      last_outcome_detail: 'timeout',
    });
    expect(employeePresenceContextPhrase(failed)).toBe('Last job failed: timeout');
    expect(employeePresenceSelectLabel(failed)).toBe(
      'Select Jules, Last job failed: timeout',
    );
    expect(employeePresenceStripTitle(failed)).toBe('Jules — Last job failed: timeout');
    expect(employeePresenceSelectLabel(employee({ name: 'Jules', enabled: false }))).toBe(
      'Select Jules, paused',
    );
    expect(employeePresenceStripTitle(employee({ name: 'Jules', enabled: false }))).toBe(
      'Jules — Paused',
    );
    const working = employee({ name: 'Alex', status: 'executing' });
    expect(employeePresenceContextPhrase(working)).toBe('executing');
    expect(employeePresenceSelectLabel(working)).toBe('Select Alex, executing');
    expect(employeePresenceStripTitle(working)).toBe('Alex — executing');
    expect(employeePresenceSelectLabel(employee({ name: 'Jules' }))).toBe('Select Jules');
    expect(employeePresenceStripTitle(employee({ name: 'Jules' }))).toBe('Jules');
  });

  it('resolves the selected presence strip employee for keyboard confirm', () => {
    const rows = [
      employee({ employee_id: 'e_idle', name: 'Zara' }),
      employee({ employee_id: 'e_failed', name: 'Mira', last_outcome: 'failed' }),
    ];
    expect(selectedPresenceStripEmployee(rows, 'e_failed')?.name).toBe('Mira');
    expect(selectedPresenceStripEmployee(rows, 'missing')).toBeNull();
    expect(selectedPresenceStripEmployee(rows, null)).toBeNull();
  });

  it('uses failure-aware callback speak when idle after a failed job', () => {
    const failed = employee({
      status: 'idle',
      last_outcome: 'failed',
      last_outcome_detail: 'vitest: assertion failed',
    });
    const line = employeeSpeakLine(failed, 'talk', { talkMode: 'callback', entropy: '1' });
    expect(line).toMatch(/failed|retry/i);
    expect(line).toContain('vitest: assertion failed');
    expect(line).not.toMatch(/Present\.|Yes\?/);
  });

  it('speaks a real role briefing instead of Present stubs', () => {
    const bridge = employee({
      name: 'Bridge',
      role: 'integrations',
      role_label: 'Integrations Engineer',
      owns: 'connectors, watch service, and cross-repo wiring',
      status: 'idle',
      last_outcome: 'failed',
      last_outcome_detail: 'cursor agent unavailable',
    });
    const talk = employeeSpeakLine(bridge, 'talk', { talkMode: 'intro' });
    expect(talk).toContain('Bridge');
    expect(talk).toContain('connectors');
    expect(talk).toContain('cursor agent unavailable');
    expect(talk).not.toMatch(/Present\.|On deck\.|Ready to help/);

    const status = employeeSpeakLine(bridge, 'status');
    expect(status).toContain('reporting in');
    expect(status).toContain('cursor agent unavailable');
    expect(status).toMatch(/try again|explain what happened/i);
  });

  it('maps working status, glow tone, and talk lines', () => {
    expect(employeeIsWorking('idle')).toBe(false);
    expect(employeeIsWorking('executing')).toBe(true);
    expect(employeeGlowTone(employee({ role: 'backend' }))).toBe('backend');
    expect(employeeGlowTone(employee({ role: 'lead', primary: true }))).toBe('lead');
    expect(employeeTalkLine(employee({ status: 'idle' }))).toBeNull();
    expect(employeeTalkLine(employee({ status: 'executing' }))).toContain('In progress');
    expect(employeeSpeakLine(employee({ status: 'idle' }), 'talk')).toContain('Shell');
    expect(employeeSpeakLine(employee({ status: 'idle' }), 'talk')).toContain('What do you need');
    expect(employeeSpeakLine(employee({ status: 'executing' }), 'talk', { talkMode: 'intro' })).toContain(
      'Shell',
    );
    expect(employeeSpeakLine(employee({ status: 'idle' }), 'talk', { talkMode: 'callback' })).toMatch(
      /Shell|checking in|you called/i,
    );
    expect(
      employeeSpeakLine(employee({ status: 'executing' }), 'talk', {
        talkMode: 'callback',
        entropy: '1',
      }),
    ).toMatch(/still mid-|in flight|live on|listening/i);
    expect(
      companyHasWorkingEmployees([
        employee({ status: 'idle' }),
        employee({ employee_id: 'e2', status: 'watching' }),
      ]),
    ).toBe(true);
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
    const specialist = employee({
      employee_id: 'employee-workspace_dashpro-integrations-4',
      name: 'Soren',
      role: 'integrations',
      status: 'executing',
      active_run_id: 'run_soren',
    });
    expect(employeeIsActivelyBusy(lead)).toBe(false);
    expect(
      employeeIsActivelyBusy({
        ...lead,
        active_run_id: 'run_lead',
      }),
    ).toBe(true);
    expect(employeeIsActivelyBusy(specialist)).toBe(true);
  });
});
