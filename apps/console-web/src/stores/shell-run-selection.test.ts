import { describe, expect, it } from 'vitest';

import type { RunRecord } from '../contracts/canonical';
import {
  isRunOnLocalCalendarDay,
  resolveRunHistoryRunId,
  selectLatestWorkspaceRun,
  selectPrimaryApprovalRun,
  selectPrimaryRun,
  selectRunSeamDisplayRun,
  selectWorkspacePrimaryRun,
} from './shell-run-selection';

function run(overrides: Partial<RunRecord> & Pick<RunRecord, 'run_id' | 'phase'>): RunRecord {
  return {
    workspace_id: 'workspace_alpha',
    lane_id: 'control-plane',
    mode: 'agent',
    status: 'running',
    summary: overrides.summary ?? 'Test run',
    detail: '',
    started_at: '2026-07-04T08:00:00Z',
    updated_at: '2026-07-04T08:00:00Z',
    ended_at: null,
    can_stop: true,
    can_resume: false,
    can_approve: false,
    can_review: false,
    current_step: null,
    history_ref: `history/${overrides.run_id}`,
    ...overrides,
  };
}

describe('shell run selection', () => {
  it('prefers review_ready over executing for primary run seam', () => {
    const executing = run({ run_id: 'run_exec', phase: 'executing', status: 'running' });
    const reviewReady = run({
      run_id: 'run_review',
      phase: 'review_ready',
      status: 'review',
      can_resume: true,
      summary: 'Read README.md',
    });

    expect(selectPrimaryRun([executing, reviewReady])?.run_id).toBe('run_review');
    expect(selectPrimaryRun([reviewReady, executing])?.run_id).toBe('run_review');
  });

  it('prefers executing run over awaiting_approval for primary run seam', () => {
    const executing = run({ run_id: 'run_exec', phase: 'executing', status: 'running' });
    const approval = run({
      run_id: 'run_approval',
      phase: 'awaiting_approval',
      status: 'blocked',
      can_approve: true,
    });

    expect(selectPrimaryRun([approval, executing])?.run_id).toBe('run_exec');
    expect(selectPrimaryApprovalRun([approval, executing])?.run_id).toBe('run_approval');
  });

  it('prefers executing over queued so Start now is visible in the status bar', () => {
    const queued = run({
      run_id: 'run_queued',
      phase: 'queued',
      status: 'queued',
      updated_at: '2026-07-30T16:00:00Z',
    });
    const executing = run({
      run_id: 'run_exec',
      phase: 'executing',
      status: 'running',
      updated_at: '2026-07-30T15:00:00Z',
    });

    expect(selectPrimaryRun([queued, executing])?.run_id).toBe('run_exec');
    expect(selectWorkspacePrimaryRun([queued, executing])?.run_id).toBe('run_exec');
  });

  it('surfaces awaiting_approval when it is the only active run', () => {
    const approval = run({
      run_id: 'run_approval',
      phase: 'awaiting_approval',
      status: 'blocked',
      can_approve: true,
    });

    expect(selectPrimaryRun([approval])?.run_id).toBe('run_approval');
    expect(selectPrimaryApprovalRun([approval])?.run_id).toBe('run_approval');
  });

  it('returns null for workspace primary run when only terminal runs exist', () => {
    const completed = run({
      run_id: 'run_done',
      phase: 'completed',
      status: 'done',
      can_stop: false,
    });

    expect(selectWorkspacePrimaryRun([completed])).toBeNull();
    expect(selectPrimaryRun([completed])).toBeNull();
  });

  it('selects the latest workspace run by updated_at', () => {
    const older = run({
      run_id: 'run_old',
      phase: 'completed',
      status: 'done',
      updated_at: '2026-07-14T08:00:00Z',
    });
    const newer = run({
      run_id: 'run_new',
      phase: 'completed',
      status: 'done',
      updated_at: '2026-07-14T12:00:00Z',
    });

    expect(selectLatestWorkspaceRun([older, newer])?.run_id).toBe('run_new');
  });

  it('shows the latest completed run from today in the run seam when idle', () => {
    const now = new Date();
    const todayStamp = new Date(
      now.getFullYear(),
      now.getMonth(),
      now.getDate(),
      12,
      0,
      0,
    ).toISOString();
    const yesterdayStamp = new Date(
      now.getFullYear(),
      now.getMonth(),
      now.getDate() - 1,
      12,
      0,
      0,
    ).toISOString();

    const completed = run({
      run_id: 'run_done',
      phase: 'completed',
      status: 'done',
      updated_at: todayStamp,
      can_stop: false,
    });

    expect(selectRunSeamDisplayRun([completed])?.run_id).toBe('run_done');
    expect(isRunOnLocalCalendarDay(completed, now)).toBe(true);
    expect(
      isRunOnLocalCalendarDay(completed, new Date(yesterdayStamp)),
    ).toBe(false);

    const yesterday = run({
      run_id: 'run_yesterday',
      phase: 'completed',
      status: 'done',
      updated_at: yesterdayStamp,
    });
    expect(selectRunSeamDisplayRun([yesterday])).toBeNull();
  });

  it('resolves run history to linked run when workspace is idle', () => {
    const completed = run({
      run_id: 'run_done',
      phase: 'completed',
      status: 'done',
      updated_at: '2026-07-14T12:00:00Z',
    });

    expect(resolveRunHistoryRunId([completed], 'run_done')).toBe('run_done');
    expect(resolveRunHistoryRunId([completed])).toBe('run_done');
  });

  it('scopes workspace primary run to the provided workspace items only', () => {
    const executing = run({
      run_id: 'run_exec',
      workspace_id: 'workspace_alpha',
      phase: 'executing',
    });
    const otherWorkspace = run({
      run_id: 'run_other',
      workspace_id: 'workspace_beta',
      phase: 'executing',
    });

    expect(selectWorkspacePrimaryRun([executing])?.run_id).toBe('run_exec');
    expect(selectWorkspacePrimaryRun([otherWorkspace])?.run_id).toBe('run_other');
    expect(selectWorkspacePrimaryRun([])).toBeNull();
  });
});
