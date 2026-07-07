import { describe, expect, it } from 'vitest';

import type { RunRecord } from '../contracts/canonical';

import {
  buildOperatorRunStripView,
  buildReviewReadyStripGroups,
  isAutoCompleteRunSummary,
  shouldHideLiveExecutionFeed,
} from './operator-run-strip-view';

function run(partial: Partial<RunRecord> & Pick<RunRecord, 'run_id' | 'summary'>): RunRecord {
  return {
    workspace_id: 'workspace_dashpro',
    mode: 'agent',
    status: 'review',
    phase: 'review_ready',
    detail: '',
    lane_id: 'lane_a',
    started_at: '2026-07-07T20:00:00Z',
    updated_at: '2026-07-07T20:05:00Z',
    ended_at: null,
    can_stop: false,
    can_resume: true,
    can_approve: false,
    can_review: true,
    current_step: null,
    history_ref: 'hist_test',
    ...partial,
  };
}

describe('operator-run-strip-view', () => {
  it('detects auto-complete summaries', () => {
    expect(isAutoCompleteRunSummary('git status')).toBe(true);
    expect(isAutoCompleteRunSummary('read README.md')).toBe(true);
    expect(isAutoCompleteRunSummary('deploy prod')).toBe(false);
  });

  it('groups duplicate git status runs', () => {
    const groups = buildReviewReadyStripGroups([
      run({ run_id: 'run_a', summary: 'git status' }),
      run({ run_id: 'run_b', summary: 'Git status' }),
      run({ run_id: 'run_c', summary: 'check-health' }),
    ]);

    expect(groups).toHaveLength(2);
    expect(groups[0]?.label).toBe('Git status');
    expect(groups[0]?.count).toBe(2);
    expect(groups[0]?.autoComplete).toBe(true);
  });

  it('collapses duplicate one-shot queue by default', () => {
    const view = buildOperatorRunStripView({
      reviewReadyRuns: Array.from({ length: 6 }, (_, index) =>
        run({ run_id: `run_${index}`, summary: 'git status' }),
      ),
    });

    expect(view.allAutoComplete).toBe(true);
    expect(view.defaultExpanded).toBe(false);
    expect(view.headline).toContain('6×');
    expect(view.completeAllLabel).toBe('Complete all (6)');
  });

  it('hides live feed for auto-complete review backlog', () => {
    const runs = [run({ run_id: 'run_a', summary: 'git status' })];
    expect(
      shouldHideLiveExecutionFeed({
        reviewReadyRuns: runs,
        primaryActiveRun: runs[0] ?? null,
      }),
    ).toBe(true);
  });
});
