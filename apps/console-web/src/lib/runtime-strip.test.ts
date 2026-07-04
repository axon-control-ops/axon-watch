import { describe, expect, it } from 'vitest';

import type { RunRecord, RuntimeSummary } from '../contracts/canonical';
import exampleRuntimeSummary from '../../../../packages/shared-types/fixtures/runtime-summary.example.json';
import {
  buildActiveRunChipLabel,
  buildStatusBarSegments,
  buildTopbarChips,
} from './runtime-strip';

const runtimeSummary = exampleRuntimeSummary as RuntimeSummary;

const activeRun = {
  run_id: 'run_contract_baseline',
  workspace_id: 'workspace_alpha',
  phase: 'executing',
  status: 'running',
  summary: 'Contract baseline run',
  detail: 'Shared DTO layer is being verified.',
  current_step: null,
  can_stop: true,
  can_resume: false,
  can_approve: false,
} as RunRecord;

describe('runtime strip helpers', () => {
  it('builds compact run chip labels', () => {
    expect(buildActiveRunChipLabel(activeRun)).toBe('run_contract_b… · executing');
  });

  it('limits topbar chips to run, watch, and degraded', () => {
    expect(
      buildTopbarChips({
        runtimeSummary: {
          ...runtimeSummary,
          approvals: { ...runtimeSummary.approvals, pending_count: 1 },
        },
        runtimeSummaryLoadState: 'loaded',
        primaryActiveRun: activeRun,
      }),
    ).toEqual([
      { id: 'run', label: 'run_contract_b… · executing', tone: 'run' },
      { id: 'watch', label: 'watch connected', tone: 'success' },
    ]);
  });

  it('adds degraded chip when runtime summary is degraded', () => {
    expect(
      buildTopbarChips({
        runtimeSummary: {
          ...runtimeSummary,
          degraded: { active: true, reasons: ['watch summary stale'] },
        },
        runtimeSummaryLoadState: 'loaded',
        primaryActiveRun: activeRun,
      }),
    ).toEqual([
      { id: 'run', label: 'run_contract_b… · executing', tone: 'run' },
      { id: 'watch', label: 'watch connected', tone: 'success' },
      { id: 'degraded', label: 'degraded · watch summary stale', tone: 'degraded' },
    ]);
  });

  it('keeps status bar segments short and count-focused', () => {
    expect(
      buildStatusBarSegments({
        layoutModeLabel: 'Operator mode',
        workspaceId: 'workspace_smoke',
        runtimeSummary: {
          ...runtimeSummary,
          approvals: { ...runtimeSummary.approvals, pending_count: 1 },
        },
        pendingApprovals: 1,
      }),
    ).toEqual([
      { id: 'mode', label: 'Operator mode', tone: 'default' },
      { id: 'workspace', label: 'workspace_smoke', tone: 'default' },
      { id: 'watch', label: 'watch connected', tone: 'success' },
      { id: 'signals', label: 'signals: 1 · high', tone: 'warning' },
      { id: 'approvals', label: 'approvals: 1', tone: 'warning' },
    ]);
  });
});
