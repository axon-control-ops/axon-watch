import { describe, expect, it } from 'vitest';

import type { CompanyEmployeeRecord } from '../../contracts/canonical';
import { resolveActiveIdeEmployee, resolveActiveIdeEmployeeRecord, buildIdeThreadBusySet, buildIdeThreadFailureDetailTooltipMap, buildIdeThreadFailureHintMap, resolveIdeThreadEmployeeFailure, resolveIdeThreadEmployeeFailureDetailTooltip, resolveRosterSelectionForIdeThread } from './active-ide-employee';

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
    azure_voice_id: 'en-GB-HollieNeural',
    ...overrides,
  };
}

describe('resolveActiveIdeEmployee', () => {
  it('returns null when the thread has no employee_id', () => {
    expect(
      resolveActiveIdeEmployee({
        thread: {
          employee_id: null,
          employee_role: null,
          title: 'Operator handoff',
          preview_label: 'Operator handoff',
        },
        employees: [employee()],
      }),
    ).toBeNull();
  });

  it('prefers roster fields including voice', () => {
    const view = resolveActiveIdeEmployee({
      thread: {
        employee_id: 'employee-workspace_axon_watch-integrations-4',
        employee_role: 'integrations',
        title: 'Quinn · Integrations',
        preview_label: 'Quinn · Integrations',
      },
      employees: [employee()],
    });
    expect(view).toMatchObject({
      name: 'Quinn',
      initials: 'QU',
      azure_voice_id: 'en-GB-HollieNeural',
    });
  });

  it('falls back to thread title when roster is empty', () => {
    const view = resolveActiveIdeEmployee({
      thread: {
        employee_id: 'employee-workspace_axon_watch-frontend-2',
        employee_role: 'frontend',
        title: 'Jules · Frontend',
        preview_label: 'Jules · Frontend',
      },
      employees: [],
    });
    expect(view).toMatchObject({
      name: 'Jules',
      initials: 'JU',
      azure_voice_id: null,
    });
  });
});

describe('resolveIdeThreadEmployeeFailure', () => {
  it('returns null for operator threads without employee_id', () => {
    expect(
      resolveIdeThreadEmployeeFailure({
        thread: { employee_id: null },
        employees: [employee()],
      }),
    ).toBeNull();
  });

  it('surfaces last shift failure detail for teammate threads', () => {
    const hint = resolveIdeThreadEmployeeFailure({
      thread: { employee_id: 'employee-workspace_axon_watch-integrations-4' },
      employees: [
        employee({
          status: 'idle',
          last_outcome: 'failed',
          last_outcome_detail: 'vitest: assertion failed',
        }),
      ],
    });
    expect(hint).toContain('Last job failed');
    expect(hint).toContain('assertion failed');
  });

  it('ignores stale failures while the teammate is actively working', () => {
    expect(
      resolveIdeThreadEmployeeFailure({
        thread: { employee_id: 'employee-workspace_axon_watch-integrations-4' },
        employees: [
          employee({
            status: 'executing',
            last_outcome: 'failed',
            last_outcome_detail: 'timeout',
          }),
        ],
      }),
    ).toBeNull();
  });

  it('clears the failure line when a stale failed tag has a success detail', () => {
    expect(
      resolveIdeThreadEmployeeFailure({
        thread: { employee_id: 'employee-workspace_axon_watch-integrations-4' },
        employees: [
          employee({
            status: 'idle',
            last_outcome: 'failed',
            last_outcome_detail: 'Run completed',
            last_run_id: 'run_133bac69735e',
          }),
        ],
      }),
    ).toBeNull();
  });
});

describe('resolveActiveIdeEmployeeRecord', () => {
  it('returns the roster row for a teammate thread', () => {
    const row = employee({ employee_id: 'employee-workspace_axon_watch-frontend-2' });
    expect(
      resolveActiveIdeEmployeeRecord({
        thread: { employee_id: 'employee-workspace_axon_watch-frontend-2' },
        employees: [row],
      }),
    ).toBe(row);
  });

  it('returns null when the thread is not teammate-owned', () => {
    expect(
      resolveActiveIdeEmployeeRecord({
        thread: { employee_id: null },
        employees: [employee()],
      }),
    ).toBeNull();
  });
});

describe('buildIdeThreadFailureHintMap', () => {
  it('indexes failure hints by thread id for teammate tabs only', () => {
    const failed = employee({
      employee_id: 'employee-workspace_axon_watch-frontend-2',
      status: 'idle',
      last_outcome: 'failed',
      last_outcome_detail: 'vitest: assertion failed',
    });
    const hints = buildIdeThreadFailureHintMap({
      threads: [
        { thread_id: 'thread_jules', employee_id: 'employee-workspace_axon_watch-frontend-2' },
        { thread_id: 'thread_operator', employee_id: null },
        {
          thread_id: 'thread_quinn',
          employee_id: 'employee-workspace_axon_watch-integrations-4',
        },
      ],
      employees: [failed, employee()],
    });
    expect(hints.get('thread_jules')).toContain('assertion failed');
    expect(hints.has('thread_operator')).toBe(false);
    expect(hints.has('thread_quinn')).toBe(false);
  });
});

describe('buildIdeThreadBusySet', () => {
  it('marks teammate tabs busy from roster status or live stream overlay', () => {
    const executing = employee({
      employee_id: 'employee-workspace_axon_watch-frontend-2',
      status: 'executing',
    });
    const watching = employee({
      employee_id: 'employee-workspace_axon_watch-watcher-1',
      role: 'watcher',
      status: 'watching',
    });
    const busy = buildIdeThreadBusySet({
      threads: [
        { thread_id: 'thread_jules', employee_id: executing.employee_id },
        { thread_id: 'thread_cass', employee_id: watching.employee_id },
        { thread_id: 'thread_operator', employee_id: null },
      ],
      employees: [executing, watching],
      liveBusyEmployeeIds: [watching.employee_id],
    });
    expect(busy.has('thread_jules')).toBe(true);
    expect(busy.has('thread_cass')).toBe(true);
    expect(busy.has('thread_operator')).toBe(false);
  });
});

describe('resolveIdeThreadEmployeeFailureDetailTooltip', () => {
  it('returns full failure detail for teammate tabs when available', () => {
    const longDetail = `${'ActionRequiredError: '.repeat(20)}out of usage`;
    const failed = employee({
      employee_id: 'employee-workspace_axon_watch-frontend-2',
      status: 'idle',
      last_outcome: 'failed',
      last_outcome_detail: longDetail,
    });
    const tooltip = resolveIdeThreadEmployeeFailureDetailTooltip({
      thread: { employee_id: 'employee-workspace_axon_watch-frontend-2' },
      employees: [failed],
    });
    expect(tooltip).toBe(
      'Usage limits blocked the agent runtime. Restore limits, then retry.',
    );
  });
});

describe('buildIdeThreadFailureDetailTooltipMap', () => {
  it('indexes full failure detail by thread id', () => {
    const failed = employee({
      employee_id: 'employee-workspace_axon_watch-frontend-2',
      status: 'idle',
      last_outcome: 'failed',
      last_outcome_detail: 'vitest: assertion failed',
    });
    const tooltips = buildIdeThreadFailureDetailTooltipMap({
      threads: [{ thread_id: 'thread_jules', employee_id: 'employee-workspace_axon_watch-frontend-2' }],
      employees: [failed],
    });
    expect(tooltips.get('thread_jules')).toBe('vitest: assertion failed');
  });
});

describe('resolveRosterSelectionForIdeThread', () => {
  it('follows teammate-owned chat tabs when the roster knows that employee', () => {
    const rows = [
      employee({ employee_id: 'e_jules' }),
      employee({ employee_id: 'e_quinn', name: 'Quinn' }),
    ];
    expect(
      resolveRosterSelectionForIdeThread({
        threadEmployeeId: 'e_jules',
        employees: rows,
        currentSelectionId: 'e_quinn',
      }),
    ).toBe('e_jules');
  });

  it('keeps the current selection for operator threads or unknown ids', () => {
    const rows = [employee({ employee_id: 'e_jules' })];
    expect(
      resolveRosterSelectionForIdeThread({
        threadEmployeeId: null,
        employees: rows,
        currentSelectionId: 'e_jules',
      }),
    ).toBe('e_jules');
    expect(
      resolveRosterSelectionForIdeThread({
        threadEmployeeId: 'missing',
        employees: rows,
        currentSelectionId: 'e_jules',
      }),
    ).toBe('e_jules');
  });
});
