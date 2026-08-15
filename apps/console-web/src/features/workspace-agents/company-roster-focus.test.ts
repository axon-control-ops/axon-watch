import { describe, expect, it } from 'vitest';

import {
  buildPendingDecisionComposerDraft,
  buildPendingDecisionOptionAnswer,
  companyPendingDecisionHint,
  failedShiftSubjectFromDecisionTitle,
  findRosterEmployeeByRole,
  pendingDecisionCardOptions,
  pendingDecisionDirectResolution,
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

  it('builds a continuation draft from title-only watcher decisions', () => {
    const draft = buildPendingDecisionComposerDraft(
      employee({
        name: 'Cass',
        role: 'watcher',
        role_label: 'Watcher',
        pending_decision_title: 'Dana (lead) last shift failed',
        pending_decision_reason: 'Lead fan-out stalled on worker dispatch.',
      }),
    );

    expect(draft).toContain('Decision required — Dana (lead) last shift failed');
    expect(draft).toContain('Cass is holding this decision for Dana (lead)');
    expect(draft).toContain('Context: Lead fan-out stalled');
    expect(draft).toContain('My decision:');
  });

  it('offers executable recovery controls when a receipt has no authored options', () => {
    const pending = employee({
      pending_decision_id: 'auton-failed-shift',
      pending_decision_title: 'Lila (frontend) last shift failed',
    });

    expect(pendingDecisionCardOptions(pending).map((option) => option.label)).toEqual([
      'Approve bounded recovery',
      'Dismiss alert',
    ]);
    expect(buildPendingDecisionComposerDraft(pending)).toContain(
      'Approve bounded recovery',
    );
    const [approve, reject] = pendingDecisionCardOptions(pending);
    expect(pendingDecisionDirectResolution(approve?.id)).toBe('approved');
    expect(pendingDecisionDirectResolution(reject?.id)).toBe('rejected');
    expect(pendingDecisionDirectResolution('1')).toBeNull();
  });
});
