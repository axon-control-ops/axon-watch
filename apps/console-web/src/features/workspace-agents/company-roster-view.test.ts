import { describe, expect, it } from 'vitest';

import {
  companyHasWorkingEmployees,
  companyHeadline,
  employeeGlowTone,
  employeeIsWorking,
  employeeMetaLine,
  employeeStatusLabel,
  employeeTalkLine,
  employeeSpeakLine,
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

  it('maps working status, glow tone, and talk lines', () => {
    expect(employeeIsWorking('idle')).toBe(false);
    expect(employeeIsWorking('executing')).toBe(true);
    expect(employeeGlowTone(employee({ role: 'backend' }))).toBe('backend');
    expect(employeeGlowTone(employee({ role: 'lead', primary: true }))).toBe('lead');
    expect(employeeTalkLine(employee({ status: 'idle' }))).toBeNull();
    expect(employeeTalkLine(employee({ status: 'executing' }))).toContain('Working on');
    expect(employeeSpeakLine(employee({ status: 'idle' }), 'talk')).toContain('Ready to help');
    expect(employeeSpeakLine(employee({ status: 'executing' }), 'talk', { talkMode: 'intro' })).toContain(
      'Shell Craft here',
    );
    expect(employeeSpeakLine(employee({ status: 'idle' }), 'talk', { talkMode: 'callback' })).not.toContain(
      'Ready to help',
    );
    expect(
      employeeSpeakLine(employee({ status: 'executing' }), 'talk', {
        talkMode: 'callback',
        entropy: '1',
      }),
    ).toMatch(/Yep|You need me|Here —|Listening|Yes boss|On it already/);
    expect(
      companyHasWorkingEmployees([
        employee({ status: 'idle' }),
        employee({ employee_id: 'e2', status: 'watching' }),
      ]),
    ).toBe(true);
  });
});
