import { describe, expect, it } from 'vitest';

import type { OperatorBriefing, RunRecord, RuntimeSummary } from '../contracts/canonical';
import exampleBriefing from '../../../../packages/shared-types/fixtures/operator-briefing.example.json';
import exampleRuntimeSummary from '../../../../packages/shared-types/fixtures/runtime-summary.example.json';

import {
  buildOperatorMissionSteps,
  operatorExecutionStage,
  operatorLiveFeed,
  operatorMissionCards,
  operatorMissionChips,
  operatorMissionSummary,
  operatorRadarTone,
  operatorStatusAdvise,
  operatorStatusHeadline,
  operatorStatusMetrics,
  operatorStatusRail,
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

  it('prefers workspace-scoped review-ready counts over global briefing notice', () => {
    expect(
      operatorStatusHeadline({
        briefing: {
          ...briefing,
          notice: '52 runs are ready for your review.',
        },
        loadState: 'loaded',
        primaryActiveRun: activeRun,
        workspaceReviewReadyCount: 17,
      }),
    ).toBe('17 runs are ready for your review in this workspace.');
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

  it('builds a mission summary for the primary run', () => {
    const summary = operatorMissionSummary({
      workspaceId: 'workspace_smoke',
      runtimeSummary,
      primaryActiveRun: activeRun,
    });

    expect(summary.runId).toBe('run_smoke');
    expect(summary.displayName).toBe('Smoke run');
    expect(summary.shortId).toBe('smoke');
    expect(summary.phase).toContain('REVIEW READY');
    expect(summary.workspace).toBe('workspace_smoke');
    expect(summary.watchConnected).toBe(true);
  });

  it('builds a bounded mission timeline from receipts and current step', () => {
    const steps = buildOperatorMissionSteps({
      historyRows: [
        {
          id: '1',
          label: 'Run created',
          timestamp: '2026-07-04T07:00:00Z',
        },
        {
          id: '2',
          label: 'Command execution recorded',
          timestamp: '2026-07-04T07:10:00Z',
        },
      ],
      currentStep: 'Review when ready',
      advise: 'Approve test run to continue execution.',
    });

    expect(steps).toHaveLength(4);
    expect(steps[0]?.tone).toBe('done');
    expect(steps[2]?.tone).toBe('active');
    expect(steps[3]?.tone).toBe('pending');
  });

  it('builds mission cards and action chips from runtime state', () => {
    const cards = operatorMissionCards({
      runtimeSummary,
      briefing,
      pendingApprovals: 1,
      lastAgentMessage: 'Executed `git_status` (ok) for run run_smoke.',
    });
    const chips = operatorMissionChips({
      lastReceipt: 'Operator approved the run to continue execution',
      advise: 'Approve test run to continue execution.',
      runtimeSummary,
      briefing,
      pendingApprovals: 1,
    });

    expect(cards).toHaveLength(4);
    expect(cards[0]?.value).toContain('git_status');
    expect(cards[3]?.tone).toBe('attention');
    expect(chips).toHaveLength(3);
    expect(chips[2]?.value).toContain('Approval boundary');
  });

  it('builds an execution stage with a dominant current step', () => {
    const stage = operatorExecutionStage({
      workspaceId: 'workspace_smoke',
      runtimeSummary,
      briefing,
      loadState: 'loaded',
      primaryActiveRun: activeRun,
    });

    expect(stage.runId).toBe('run_smoke');
    expect(stage.displayName).toBe('Smoke run');
    expect(stage.shortId).toBe('smoke');
    expect(stage.phaseProgress).toBeGreaterThan(0);
    expect(stage.currentStep).toBe('Review when ready');
    expect(stage.notice).toBe(briefing.notice);
    expect(stage.decide).toBe(briefing.executive_rhythm.decide);
  });

  it('builds a bounded live feed from receipts and agent output', () => {
    const feed = operatorLiveFeed({
      historyRows: [
        { id: '1', label: 'Run created', timestamp: '2026-07-04T07:00:00Z' },
        { id: '2', label: 'Command execution recorded', timestamp: '2026-07-04T07:10:00Z' },
      ],
      currentStep: 'Review when ready',
      lastAgentMessage: 'Executed `git_status` (ok) for run run_smoke.',
      advise: 'Approve test run to continue execution.',
      hasActiveRun: true,
    });

    expect(feed.length).toBeGreaterThan(0);
    expect(feed.some((item) => item.tone === 'active')).toBe(true);
    expect(feed.some((item) => item.tone === 'info')).toBe(true);
  });

  it('builds a compact status rail for secondary telemetry', () => {
    const rail = operatorStatusRail({
      workspaceId: 'workspace_smoke',
      runtimeSummary,
      briefing,
      pendingApprovals: 1,
    });

    expect(rail).toHaveLength(5);
    expect(rail[0]?.value).toBe('online');
    expect(rail[3]?.value).toBe('ready');
    expect(rail[4]?.value).toBe('workspace_smoke');
  });

  it('reflects paused and executing phases in mission control projections', () => {
    const pausedRun: RunRecord = {
      ...activeRun,
      status: 'waiting',
      phase: 'paused',
      can_stop: true,
      can_resume: true,
      current_step: 'Run paused by operator stop',
    };
    const executingRun: RunRecord = {
      ...activeRun,
      status: 'running',
      phase: 'executing',
      can_stop: true,
      can_resume: false,
      current_step: 'Executing thin-slice work',
    };

    expect(
      operatorMissionSummary({
        workspaceId: 'workspace_smoke',
        runtimeSummary,
        primaryActiveRun: pausedRun,
      }).phase,
    ).toBe('PAUSED');

    expect(
      operatorStatusMetrics({
        workspaceId: 'workspace_smoke',
        runtimeSummary,
        runtimeSummaryLoadState: 'loaded',
        briefing,
        briefingLoadState: 'loaded',
        primaryActiveRun: executingRun,
        pendingApprovals: 0,
      })[1]?.value,
    ).toContain('EXECUTE');

    expect(
      operatorExecutionStage({
        workspaceId: 'workspace_smoke',
        runtimeSummary,
        briefing,
        loadState: 'loaded',
        primaryActiveRun: pausedRun,
      }).currentStep,
    ).toBe('Run paused by operator stop');
  });

  it('reflects awaiting approval boundary in mission control projections', () => {
    const approvalRun: RunRecord = {
      ...activeRun,
      status: 'blocked',
      phase: 'awaiting_approval',
      can_stop: true,
      can_resume: false,
      can_approve: true,
      can_review: false,
      current_step: 'Awaiting operator approval',
    };

    expect(
      operatorMissionSummary({
        workspaceId: 'workspace_smoke',
        runtimeSummary,
        primaryActiveRun: approvalRun,
      }).phase,
    ).toBe('AWAITING APPROVAL');

    const metrics = operatorStatusMetrics({
      workspaceId: 'workspace_smoke',
      runtimeSummary,
      runtimeSummaryLoadState: 'loaded',
      briefing,
      briefingLoadState: 'loaded',
      primaryActiveRun: approvalRun,
      pendingApprovals: 1,
    });

    expect(metrics[1]?.value).toContain('AWAITING APPROVAL');
    expect(metrics[4]?.value).toBe('1');
    expect(metrics[4]?.tone).toBe('attention');
  });
});
