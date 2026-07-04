import { describe, expect, it } from 'vitest';

import type { OperatorBriefing, RunRecord, RuntimeSummary } from '../contracts/canonical';
import exampleBriefing from '../../../../packages/shared-types/fixtures/operator-briefing.example.json';
import exampleRuntimeSummary from '../../../../packages/shared-types/fixtures/runtime-summary.example.json';

import {
  operatorRadarTone,
  operatorStatusAdvise,
  operatorStatusHeadline,
  operatorStatusMetrics,
} from './operator-status-radar-view';

const briefing = exampleBriefing as unknown as OperatorBriefing;
const runtimeSummary = exampleRuntimeSummary as unknown as RuntimeSummary;

const activeRun: RunRecord = {
  run_id: 'run_smoke',
  workspace_id: 'workspace_smoke',
  mode: 'agent',
  status: 'review',
  phase: 'review_ready',
  summary: 'Smoke run',
  detail: 'Ready for review',
  lane_id: 'control-plane',
  started_at: '2026-07-04T07:00:00Z',
  updated_at: '2026-07-04T08:00:00Z',
  ended_at: null,
  can_stop: true,
  can_resume: false,
  can_approve: false,
  can_review: true,
  current_step: 'Review when ready',
  history_ref: 'run_smoke',
};

describe('operator status radar view', () => {
  it('prioritizes attention tone when approvals are pending', () => {
    expect(
      operatorRadarTone({
        runtimeSummary,
        briefing,
        pendingApprovals: 1,
      }),
    ).toBe('attention');
  });

  it('uses briefing notice as the status headline', () => {
    expect(
      operatorStatusHeadline({
        briefing,
        loadState: 'loaded',
        primaryActiveRun: activeRun,
      }),
    ).toBe(briefing.notice);
  });

  it('builds DTO-backed metrics for the operator panel', () => {
    const metrics = operatorStatusMetrics({
      workspaceId: 'workspace_smoke',
      runtimeSummary,
      runtimeSummaryLoadState: 'loaded',
      briefing,
      briefingLoadState: 'loaded',
      primaryActiveRun: activeRun,
      pendingApprovals: 1,
    });

    expect(metrics).toHaveLength(6);
    expect(metrics[0]?.value).toBe('workspace_smoke');
    expect(metrics[1]?.value).toContain('REVIEW READY');
    expect(metrics[3]?.value).toBe('1');
    expect(metrics[4]?.value).toBe('1');
    expect(metrics[4]?.tone).toBe('attention');
  });

  it('surfaces briefing advise copy', () => {
    expect(
      operatorStatusAdvise({
        briefing,
        loadState: 'loaded',
      }),
    ).toBe(briefing.advise);
  });
});
