import { describe, expect, it } from 'vitest';

import type { CompanyEmployeeRecord } from '../../contracts/canonical';
import {
  employeeAssignDraft,
  employeeChatComposerMode,
  employeeChatDraft,
  employeeComposerOpenPayload,
  employeeDockDisplayActions,
  employeeQuickActions,
  employeeReceiptsDraft,
  employeeRetryDraft,
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
  it('builds assign drafts; talk and status leave the composer empty', () => {
    const row = employee();
    expect(employeeTalkDraft(row)).toBe('');
    expect(employeeStatusDraft(row)).toBe('');
    expect(employeeAssignDraft(row)).toBe(
      'Assign to Shell Craft (console UI/UX, dock, and shell polish): ',
    );
    expect(employeeChatDraft(row, 'talk')).toBe('');
    expect(employeeChatDraft(row, 'status')).toBe('');
  });

  it('picks composer mode by chat kind', () => {
    expect(employeeChatComposerMode('status')).toBe('ask');
    expect(employeeChatComposerMode('talk')).toBe('agent');
    expect(employeeChatComposerMode('assign')).toBe('agent');
  });

  it('bundles composer mode and draft for roster and dock open flows', () => {
    const failed = employee({
      status: 'idle',
      last_outcome: 'failed',
      last_outcome_detail: 'vitest: assertion failed',
      last_run_id: 'run_failed_abc123',
    });
    expect(employeeComposerOpenPayload(failed, 'retry')).toEqual({
      mode: 'agent',
      draft: employeeRetryDraft(failed),
    });
    expect(employeeComposerOpenPayload(failed, 'receipts')).toEqual({
      mode: 'ask',
      draft: employeeReceiptsDraft(failed),
    });
    expect(employeeComposerOpenPayload(failed, 'talk')).toEqual({
      mode: 'agent',
      draft: '',
    });
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
      'toggle_enabled',
      'briefing',
    ]);

    const watcherActions = employeeQuickActions(employee({ role: 'watcher', name: 'Night Watch' }));
    expect(watcherActions.map((action) => action.id)).toEqual([
      'talk',
      'status',
      'assign',
      'toggle_enabled',
      'attention',
    ]);
  });

  it('offers pause/enable and stop when a shift is active', () => {
    const paused = employee({ enabled: false });
    expect(employeeQuickActions(paused).find((action) => action.id === 'toggle_enabled')?.label).toBe(
      'Enable agent',
    );
    const working = employee({ active_run_id: 'run_123', status: 'executing' });
    expect(employeeQuickActions(working).map((action) => action.id)).toContain('stop');
  });

  it('offers retry shift when the last outcome failed and the teammate is idle', () => {
    const failed = employee({
      status: 'idle',
      last_outcome: 'failed',
      last_outcome_detail: 'vitest: assertion failed',
      last_run_id: 'run_failed_abc123',
    });
    expect(employeeQuickActions(failed).map((action) => action.id)).toEqual([
      'retry',
      'receipts',
      'talk',
      'status',
      'assign',
      'toggle_enabled',
    ]);
    expect(employeeQuickActions(failed).find((action) => action.id === 'retry')?.label).toBe(
      'Retry shift',
    );
    expect(employeeQuickActions(failed).find((action) => action.id === 'receipts')?.label).toBe(
      'Explain receipts',
    );
    expect(employeeRetryDraft(failed)).toContain('Retry the last failed shift');
    expect(employeeRetryDraft(failed)).toContain('vitest: assertion failed');
    expect(employeeChatDraft(failed, 'retry')).toBe(employeeRetryDraft(failed));
    expect(employeeReceiptsDraft(failed)).toContain('run_failed_abc123');
    expect(employeeReceiptsDraft(failed)).toContain('vitest: assertion failed');
    expect(employeeChatComposerMode('receipts')).toBe('ask');
  });

  it('uses continuation prompt when the last failure was a SIGTERM agent session', () => {
    const interrupted = employee({
      status: 'idle',
      last_outcome: 'failed',
      last_outcome_detail: 'Cursor CLI exited with status 143.',
      last_run_id: 'run_1787e8045f65',
    });
    const retry = employeeRetryDraft(interrupted);
    expect(retry).toContain('Continue the interrupted run from after the server restart');
    expect(retry).not.toContain('status 143');
    expect(employeeQuickActions(interrupted).find((action) => action.id === 'retry')?.label).toBe(
      'Continue shift',
    );
  });

  it('uses continuation prompt when the last failure was a server restart', () => {
    const interrupted = employee({
      status: 'idle',
      last_outcome: 'failed',
      last_outcome_detail: 'Run interrupted by control-plane restart',
      last_run_id: 'run_5c0253a7808a',
    });
    const retry = employeeRetryDraft(interrupted);
    expect(retry).toContain('Continue the interrupted run from after the server restart');
    expect(retry).not.toContain('Run interrupted by control-plane restart');
    const receipts = employeeReceiptsDraft(interrupted);
    expect(receipts).toContain('run_5c0253a7808a');
    expect(receipts).toContain('Continue the interrupted run from after the server restart');
  });

  it('normalizes lane b wrapper noise in retry and receipts drafts', () => {
    const wrapped =
      'Lane B agent fallback reply generated (CLI runtime timed out after 240s.; Cursor Cloud Agent unavailable; Codex CLI (local) unavailable; Codex Cloud Task unavailable)';
    const failed = employee({
      status: 'idle',
      last_outcome: 'failed',
      last_outcome_detail: wrapped,
      last_run_id: 'run_34e5116fecb6',
    });
    expect(employeeRetryDraft(failed)).toContain('CLI runtime timed out after 240s.');
    expect(employeeRetryDraft(failed)).not.toContain('Lane B agent fallback');
    expect(employeeRetryDraft(failed)).not.toContain('Codex Cloud Task');
    expect(employeeReceiptsDraft(failed)).toContain('CLI runtime timed out after 240s.');
    expect(employeeReceiptsDraft(failed)).not.toContain('Lane B agent fallback');
  });

  it('uses usage-limit guidance in retry and receipts drafts', () => {
    const failed = employee({
      status: 'idle',
      last_outcome: 'failed',
      last_outcome_detail:
        "Lane B agent fallback reply generated (ActionRequiredError: You're out of usage.)",
      last_run_id: 'run_7ae605411d4d',
    });
    expect(employeeRetryDraft(failed)).toContain('Usage limits blocked the last shift');
    expect(employeeRetryDraft(failed)).toContain('Once limits are restored');
    expect(employeeRetryDraft(failed)).not.toContain('ActionRequiredError');
    expect(employeeReceiptsDraft(failed)).toContain('run_7ae605411d4d');
    expect(employeeReceiptsDraft(failed)).toContain('usage limits blocked the agent runtime');
    expect(employeeReceiptsDraft(failed)).not.toContain('ActionRequiredError');
  });

  it('uses runtime-auth guidance in retry and receipts drafts', () => {
    const failed = employee({
      status: 'idle',
      last_outcome: 'failed',
      last_outcome_detail:
        'Lane B agent fallback reply generated (Cursor is installed but not signed in. Run `cursor agent login` or unlock /vault.; Cursor Cloud Agent unavailable)',
      last_run_id: 'run_43ca086d22d4',
    });
    expect(employeeRetryDraft(failed)).toContain('Runtime auth blocked the last shift');
    expect(employeeRetryDraft(failed)).toContain('cursor agent login');
    expect(employeeRetryDraft(failed)).not.toContain('Lane B agent fallback');
    expect(employeeReceiptsDraft(failed)).toContain('run_43ca086d22d4');
    expect(employeeReceiptsDraft(failed)).toContain('runtime auth is not ready');
  });

  it('hides duplicate view receipts in the dock when the run link is shown', () => {
    const failed = employee({
      status: 'idle',
      last_outcome: 'failed',
      last_outcome_detail: 'vitest: assertion failed',
      last_run_id: 'run_failed_abc123',
    });
    const actions = employeeQuickActions(failed);
    expect(actions.map((action) => action.id)).toContain('receipts');
    expect(employeeDockDisplayActions(actions, failed).map((action) => action.id)).toEqual([
      'retry',
      'talk',
      'status',
      'assign',
      'toggle_enabled',
    ]);
  });

  it('omits view receipts when a failed shift has no run id', () => {
    const failed = employee({
      status: 'idle',
      last_outcome: 'failed',
      last_outcome_detail: 'unknown failure',
    });
    expect(employeeQuickActions(failed).map((action) => action.id)).toEqual([
      'retry',
      'talk',
      'status',
      'assign',
      'toggle_enabled',
    ]);
  });
});
