import { describe, expect, it } from 'vitest';

import type { CompanyEmployeeRecord } from '../../contracts/canonical';
import {
  employeeAssignDraft,
  employeeChatComposerMode,
  employeeChatDraft,
  employeeQuickActions,
  employeeStatusDraft,
  employeeSurfaceAction,
  employeeTalkDraft,
} from './company-roster-actions';

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

describe('company-roster-actions', () => {
  it('builds status and assign drafts; talk leaves the composer empty', () => {
    const row = employee();
    expect(employeeTalkDraft(row)).toBe('');
    expect(employeeStatusDraft(row)).toContain('Ask Shell Craft for a short status');
    expect(employeeAssignDraft(row)).toBe(
      'Assign to Shell Craft (console UI/UX, dock, and shell polish): ',
    );
    expect(employeeChatDraft(row, 'talk')).toBe('');
  });

  it('picks composer mode by chat kind', () => {
    expect(employeeChatComposerMode('status')).toBe('ask');
    expect(employeeChatComposerMode('talk')).toBe('agent');
    expect(employeeChatComposerMode('assign')).toBe('agent');
  });

  it('maps lead to briefing and watcher to signals', () => {
    expect(employeeSurfaceAction(employee({ role: 'lead', primary: true }))).toBe('briefing');
    expect(employeeSurfaceAction(employee({ role: 'watcher' }))).toBe('attention');
    expect(employeeSurfaceAction(employee())).toBeNull();
  });

  it('includes role-specific surface action in quick actions', () => {
    const leadActions = employeeQuickActions(employee({ role: 'lead', primary: true }));
    expect(leadActions.map((action) => action.id)).toEqual([
      'talk',
      'status',
      'assign',
      'briefing',
    ]);

    const watcherActions = employeeQuickActions(employee({ role: 'watcher', name: 'Night Watch' }));
    expect(watcherActions.map((action) => action.id)).toEqual([
      'talk',
      'status',
      'assign',
      'attention',
    ]);
  });
});
