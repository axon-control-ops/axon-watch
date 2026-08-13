import { describe, expect, it } from 'vitest';

import {
  buildPendingDecisionComposerDraft,
  buildPendingDecisionOptionAnswer,
  companyPendingDecisionHint,
  failedShiftSubjectFromDecisionTitle,
  findRosterEmployeeByRole,
} from './company-roster-focus';
import type { CompanyEmployeeRecord } from '../../contracts/canonical';

function employee(
  overrides: Partial<CompanyEmployeeRecord> = {},
): CompanyEmployeeRecord {
  return {
    employee_id: 'employee-demo-frontend-0',
    workspace_id: 'workspace_demo',
    name: 'Lila',
    role: 'frontend',
    role_label: 'Frontend',
    schedule: 'continuous',
    schedule_label: 'Continuous',
    status: 'idle',
    owns: 'UI',
    enabled: true,
    primary: false,
    ...overrides,
  };
}

describe('failedShiftSubjectFromDecisionTitle', () => {
  it('parses failed-shift autonomy titles', () => {
    expect(failedShiftSubjectFromDecisionTitle('Dana (lead) last shift failed')).toEqual({
      name: 'Dana',
      role: 'lead',
    });
    expect(failedShiftSubjectFromDecisionTitle('Soren (integrations) last shift failed')).toEqual({
      name: 'Soren',
      role: 'integrations',
    });
    expect(failedShiftSubjectFromDecisionTitle('Retry lead shift')).toBeNull();
  });
});

describe('findRosterEmployeeByRole', () => {
  it('finds a teammate by role slug', () => {
    const rows = [
      employee({ employee_id: 'e-lead', role: 'lead', name: 'Dana' }),
      employee({ employee_id: 'e-int', role: 'integrations', name: 'Soren' }),
    ];
    expect(findRosterEmployeeByRole(rows, 'integrations')?.name).toBe('Soren');
    expect(findRosterEmployeeByRole(rows, 'backend')).toBeNull();
  });
});

describe('companyPendingDecisionHint', () => {
  it('names the decision holder and failed-shift subject when they differ', () => {
    expect(
      companyPendingDecisionHint([
        employee({
          name: 'Cass',
          role: 'watcher',
          pending_decision_id: 'auton-1',
          pending_decision_title: 'Dana (lead) last shift failed',
        }),
      ]),
    ).toContain('Cass needs your decision about Dana (lead)');
  });
});

describe('buildPendingDecisionOptionAnswer', () => {
  it('formats a structured autonomy answer', () => {
    const answer = buildPendingDecisionOptionAnswer(
      employee({
        pending_decision_prompt: 'Dana last shift failed — retry or escalate?',
      }),
      { id: 'retry', label: 'Retry lead shift' },
    );
    expect(answer).toContain('Selected option retry: Retry lead shift');
    expect(answer).toContain('(answer to: Dana last shift failed');
  });
});

describe('buildPendingDecisionComposerDraft', () => {
  it('seeds prompt and decision options for the composer', () => {
    const draft = buildPendingDecisionComposerDraft(
      employee({
        pending_decision_prompt: 'Dana last shift failed — retry or escalate?',
        pending_decision_options: [
          { id: 'retry', label: 'Retry lead shift' },
          { id: 'escalate', label: 'Escalate to operator' },
        ],
      }),
    );

    expect(draft).toContain('Dana last shift failed');
    expect(draft).toContain('Retry lead shift');
    expect(draft).toContain('My decision:');
  });
});
