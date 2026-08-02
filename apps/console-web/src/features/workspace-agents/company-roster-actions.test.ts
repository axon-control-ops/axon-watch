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
import { employeeFailureBlocksAutoRetry } from './company-roster-view';

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
    // Status is voice + focus only — must not demote Full Access into Ask/consultative.
    expect(employeeChatComposerMode('status')).toBeNull();
    expect(employeeChatComposerMode('talk')).toBe('agent');
    expect(employeeChatComposerMode('assign')).toBe('agent');
    expect(employeeChatComposerMode('receipts')).toBe('ask');
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
    expect(employeeComposerOpenPayload(failed, 'status')).toEqual({
      mode: null,
      draft: '',
    });
  });

  it('does not attach Ask composerMode on the Status quick action', () => {
    const statusAction = employeeQuickActions(employee()).find((action) => action.id === 'status');
    expect(statusAction?.chatKind).toBe('status');
    expect(statusAction?.composerMode).toBeUndefined();
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
      'Try again',
    );
    expect(employeeQuickActions(failed).find((action) => action.id === 'receipts')?.label).toBe(
      'Explain what happened',
    );
    expect(employeeRetryDraft(failed)).toMatch(/My last continuous shift on .+ failed/);
    expect(employeeRetryDraft(failed)).not.toMatch(/^I am /);
    expect(employeeRetryDraft(failed)).toContain('vitest: assertion failed');
    expect(employeeRetryDraft(failed)).toContain('Confidence: N/10');
    expect(employeeRetryDraft(failed).toLowerCase()).toContain('first person');
    expect(employeeChatDraft(failed, 'retry')).toBe(employeeRetryDraft(failed));

    const missingConfidence = employee({
      status: 'idle',
      last_outcome: 'failed',
      last_outcome_detail:
        'Critical Review Clause missing: final reply must end with Confidence: N/10',
    });
    const confidenceRetry = employeeRetryDraft(missingConfidence);
    expect(confidenceRetry).toContain('closing Critical Review line');
    expect(confidenceRetry).toContain('Confidence: N/10');
    expect(confidenceRetry).not.toMatch(/My last continuous shift on .+ failed/);

    expect(employeeReceiptsDraft(failed)).toContain('run_failed_abc123');
    expect(employeeReceiptsDraft(failed)).toContain('vitest: assertion failed');
    expect(employeeReceiptsDraft(failed)).toContain('my last job');
    expect(employeeReceiptsDraft(failed)).not.toContain("Priya's");
    expect(employeeReceiptsDraft(failed)).not.toContain('Error: Run completed');
    expect(employeeChatComposerMode('receipts')).toBe('ask');
  });

  it('still offers Try again when Cursor usage is exhausted (copy warns; dock must not hide retry)', () => {
    const usageBlocked = employee({
      status: 'idle',
      last_outcome: 'failed',
      last_outcome_detail: 'ActionRequiredError: out of usage',
      last_run_id: 'run_usage_blocked',
    });
    const actions = employeeQuickActions(usageBlocked);
    expect(actions.map((action) => action.id)).toEqual([
      'retry',
      'receipts',
      'talk',
      'status',
      'assign',
      'toggle_enabled',
    ]);
    expect(actions.find((action) => action.id === 'retry')?.label).toBe('Try again');
    expect(employeeDockDisplayActions(actions, usageBlocked).map((action) => action.id)).toEqual([
      'retry',
      'talk',
      'status',
      'assign',
      'toggle_enabled',
    ]);
    expect(employeeFailureBlocksAutoRetry(usageBlocked)).toBe(true);
  });

  it('explains completed jobs without calling them failures', () => {
    const completed = employee({
      status: 'idle',
      last_outcome: 'completed',
      last_outcome_detail: 'Run completed',
      last_run_id: 'run_133bac69735e',
    });
    const draft = employeeReceiptsDraft(completed);
    expect(draft).toContain('run_133bac69735e');
    expect(draft).toContain('completed successfully');
    expect(draft).not.toMatch(/what failed|Error:/i);
  });

  it('treats success-like detail as completed even when outcome tag is stale failed', () => {
    const stale = employee({
      status: 'idle',
      last_outcome: 'failed',
      last_outcome_detail: 'Run completed',
      last_run_id: 'run_133bac69735e',
    });
    const draft = employeeReceiptsDraft(stale);
    expect(draft).toContain('completed successfully');
    expect(draft).not.toMatch(/what failed|Error:/i);
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
      'Continue',
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
    expect(employeeRetryDraft(failed)).toContain('Cursor usage signal blocked my last shift');
    expect(employeeRetryDraft(failed)).toContain('Auto+Composer or on-demand');
    expect(employeeRetryDraft(failed)).not.toContain('ActionRequiredError');

    expect(employeeReceiptsDraft(failed)).toContain('run_7ae605411d4d');
    expect(employeeReceiptsDraft(failed)).toContain('Cursor usage signal');
    expect(employeeReceiptsDraft(failed)).not.toContain('ActionRequiredError');
    expect(employeeReceiptsDraft(failed)).toContain('do not claim the whole account is exhausted');
  });

  it('uses runtime-auth guidance in retry and receipts drafts', () => {
    const failed = employee({
      status: 'idle',
      last_outcome: 'failed',
      last_outcome_detail:
        'Lane B agent fallback reply generated (Cursor is installed but not signed in. Run `cursor agent login` or unlock /vault.; Cursor Cloud Agent unavailable)',
      last_run_id: 'run_43ca086d22d4',
    });
    expect(employeeRetryDraft(failed)).toContain('Runtime auth blocked my last shift');
    expect(employeeRetryDraft(failed)).toContain('cursor agent login');
    expect(employeeRetryDraft(failed)).not.toContain('Lane B agent fallback');

    expect(employeeReceiptsDraft(failed)).toContain('run_43ca086d22d4');
    expect(employeeReceiptsDraft(failed)).toContain('login is not ready');
  });

  it('uses auth-probe guidance (not login) when the Cursor probe timed out', () => {
    const failed = employee({
      status: 'idle',
      last_outcome: 'failed',
      last_outcome_detail:
        'Lane B agent fallback reply generated (Cursor auth probe timed out. Run `cursor agent status` manually.; Cursor Cloud Agent unavailable)',
      last_run_id: 'run_probe_timeout',
    });
    expect(employeeRetryDraft(failed)).toContain('auth probe timed out');
    expect(employeeRetryDraft(failed)).toContain('cursor agent status');
    expect(employeeRetryDraft(failed)).not.toContain('cursor agent login');
    expect(employeeReceiptsDraft(failed)).toContain('auth probe timed out');
    expect(employeeReceiptsDraft(failed)).not.toContain('login is not ready');
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

  it('omits view receipts when a failed job has no run id', () => {
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

  it('offers Start now for Manual handoffs that are not live-busy', () => {
    const tasks = [
      {
        task_id: 'task_open',
        workspace_id: 'workspace_demo',
        goal: 'Ship dock polish',
        acceptance_criteria: '',
        owner_role: 'frontend',
        status: 'open' as const,
        risk: 'normal' as const,
        attempt_budget: 3,
        attempts_used: 0,
        dependencies: [],
        allowed_paths: [],
        exclusive_paths: [],
        lease_holder: null,
        lease_expires_at: null,
        run_id: null,
        plan_id: null,
        plan_key: null,
        terminal_outcome: null,
        created_at: '2026-07-30T00:00:00Z',
        updated_at: '2026-07-30T00:00:00Z',
      },
    ];
    const waiting = employeeQuickActions(employee(), {
      autonomyMode: 'manual',
      tasks,
      liveBusy: false,
    });
    expect(waiting[0]).toMatchObject({ id: 'start_now', taskId: 'task_open' });

    const busy = employeeQuickActions(employee(), {
      autonomyMode: 'manual',
      tasks,
      liveBusy: true,
    });
    expect(busy.map((action) => action.id)).not.toContain('start_now');
  });

  it('offers Semi Start now for cross-workspace handoff tickets', () => {
    const tasks = [
      {
        task_id: 'task_handoff',
        workspace_id: 'workspace_dashpro',
        goal: 'Fix child card avatar',
        acceptance_criteria: 'Complete the cross-workspace handoff from Young Eagles.',
        owner_role: 'frontend',
        status: 'open' as const,
        risk: 'normal' as const,
        attempt_budget: 3,
        attempts_used: 0,
        dependencies: [],
        allowed_paths: [],
        exclusive_paths: [],
        lease_holder: null,
        lease_expires_at: null,
        run_id: null,
        plan_id: null,
        plan_key: null,
        terminal_outcome: null,
        created_at: '2026-07-30T00:00:00Z',
        updated_at: '2026-07-30T00:00:00Z',
      },
    ];
    const actions = employeeQuickActions(employee(), {
      autonomyMode: 'semi',
      tasks,
      liveBusy: false,
    });
    expect(actions[0]).toMatchObject({ id: 'start_now', taskId: 'task_handoff' });
  });
});
