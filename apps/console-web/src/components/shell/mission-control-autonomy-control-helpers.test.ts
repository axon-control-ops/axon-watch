import { describe, expect, it } from 'vitest';

import {
  buildAutonomyTelemetryLine,
  resolveAutonomyWorkerStateLabel,
  shouldShowAutonomyAlert,
} from './mission-control-autonomy-control-helpers';

describe('mission-control-autonomy-control-helpers', () => {
  it('labels worker state from autonomy + host brake flags', () => {
    expect(resolveAutonomyWorkerStateLabel({ status: null, autonomousOn: false })).toBe(
      'Unknown',
    );
    expect(
      resolveAutonomyWorkerStateLabel({
        status: { blocked_by_env: true },
        autonomousOn: true,
      }),
    ).toBe('Blocked');
    expect(
      resolveAutonomyWorkerStateLabel({
        status: { effective_enabled: true },
        autonomousOn: true,
      }),
    ).toBe('Running');
    expect(
      resolveAutonomyWorkerStateLabel({
        status: { effective_enabled: false },
        autonomousOn: true,
      }),
    ).toBe('Armed');
    expect(
      resolveAutonomyWorkerStateLabel({
        status: { effective_enabled: false },
        autonomousOn: false,
      }),
    ).toBe('Paused');
  });

  it('builds telemetry with scan deltas and unreadiness score', () => {
    expect(
      buildAutonomyTelemetryLine({
        workerStateLabel: 'Running',
        autonomyMode: 'full',
        scan: { created_count: 2, escalated_count: 1 },
        readiness: { grade: 'blocked', score: 72 },
      }),
    ).toBe('Running · full · +2 · ↑1 · 72/100');
  });

  it('shows alert when action, feed error, brake, or unreadiness is present', () => {
    expect(
      shouldShowAutonomyAlert({
        actionMessage: null,
        feedError: null,
        blockedByEnv: false,
        readiness: { grade: 'ready', score: 100 },
      }),
    ).toBe(false);
    expect(
      shouldShowAutonomyAlert({
        actionMessage: 'ok',
        feedError: null,
        blockedByEnv: false,
        readiness: null,
      }),
    ).toBe(true);
    expect(
      shouldShowAutonomyAlert({
        actionMessage: null,
        feedError: 'boom',
        blockedByEnv: false,
        readiness: null,
      }),
    ).toBe(true);
    expect(
      shouldShowAutonomyAlert({
        actionMessage: null,
        feedError: null,
        blockedByEnv: true,
        readiness: null,
      }),
    ).toBe(true);
  });
});
