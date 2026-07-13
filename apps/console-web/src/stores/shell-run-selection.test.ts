import { describe, expect, it } from 'vitest';

import type { RunRecord } from '../contracts/canonical';
import { selectPrimaryApprovalRun, selectPrimaryRun, selectWorkspacePrimaryRun } from './shell-run-selection';

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
